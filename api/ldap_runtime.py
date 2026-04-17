"""Controlled LDAPv3-compatible runtime for sponsor JNDI proof.

This module intentionally implements only the small LDAP surface needed for a
deterministic Contoso bind/search/lookup proof. It speaks LDAP BER messages over
TCP so the provider can prove a real wire roundtrip without claiming enterprise
directory infrastructure.
"""

from __future__ import annotations

import os
import socket
import socketserver
import threading
from dataclasses import dataclass
from typing import Any


LDAP_BINDINGS: dict[str, dict[str, Any]] = {
    "jdbc/ContosoCustomerDB": {
        "type": "javax.sql.DataSource",
        "dn": "cn=ContosoCustomerDB,ou=jdbc,dc=contoso,dc=com",
        "url": "jdbc:sqlserver://db.contoso.internal:1433;databaseName=CustomerDB",
    },
    "jdbc/ContosoReportingDB": {
        "type": "javax.sql.DataSource",
        "dn": "cn=ContosoReportingDB,ou=jdbc,dc=contoso,dc=com",
        "url": "jdbc:sqlserver://rdb.contoso.internal:1433;databaseName=CustomerDB",
    },
    "jms/OrderProcessingQueue": {
        "type": "javax.jms.Queue",
        "dn": "cn=OrderProcessingQueue,ou=jms,dc=contoso,dc=com",
    },
    "jms/SupportTicketTopic": {
        "type": "javax.jms.Topic",
        "dn": "cn=SupportTicketTopic,ou=jms,dc=contoso,dc=com",
    },
    "jms/RefundApprovalQueue": {
        "type": "javax.jms.Queue",
        "dn": "cn=RefundApprovalQueue,ou=jms,dc=contoso,dc=com",
    },
    "jms/ContosoConnectionFactory": {
        "type": "javax.jms.ConnectionFactory",
        "dn": "cn=ContosoConnectionFactory,ou=jms,dc=contoso,dc=com",
    },
    "ejb/CustomerServiceBean": {
        "type": "EJB remote interface",
        "dn": "cn=CustomerServiceBean,ou=ejb,dc=contoso,dc=com",
    },
    "ejb/OrderServiceBean": {
        "type": "EJB remote interface",
        "dn": "cn=OrderServiceBean,ou=ejb,dc=contoso,dc=com",
    },
    "java:comp/env/defaultPriority": {
        "type": "java.lang.String",
        "value": "Normal",
        "dn": "cn=defaultPriority,ou=env,dc=contoso,dc=com",
    },
}

DEFAULT_BIND_DN = "cn=serviceaccount,dc=contoso,dc=com"
BASE_DN = "dc=contoso,dc=com"


def ldap_entry(name: str, binding: dict[str, Any]) -> dict[str, Any]:
    attrs = {
        "cn": [name.split("/")[-1].replace("java:comp/env/", "")],
        "javaClassName": [str(binding.get("type", "java.lang.Object"))],
        "javaFactory": ["com.contoso.naming.McpFactoryReferenceFactory"],
        "javaReferenceAddress": [str(binding.get("url") or binding.get("value") or name)],
        "mcpFactoryBindingName": [name],
    }
    return {
        "dn": str(binding.get("dn") or f"cn={name.replace('/', '_')},{BASE_DN}"),
        "attributes": attrs,
        "binding": binding,
    }


def ldap_config_ldif() -> str:
    lines = [
        f"dn: {BASE_DN}",
        "objectClass: top",
        "objectClass: domain",
        "dc: contoso",
        "",
    ]
    for name, binding in LDAP_BINDINGS.items():
        entry = ldap_entry(name, binding)
        lines.extend(
            [
                f"dn: {entry['dn']}",
                "objectClass: top",
                "objectClass: javaNamingReference",
                f"cn: {entry['attributes']['cn'][0]}",
                f"javaClassName: {entry['attributes']['javaClassName'][0]}",
                f"javaFactory: {entry['attributes']['javaFactory'][0]}",
                f"javaReferenceAddress: {entry['attributes']['javaReferenceAddress'][0]}",
                f"mcpFactoryBindingName: {name}",
                "",
            ]
        )
    return "\n".join(lines)


def _ber_len(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(encoded)]) + encoded


def _ber_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _ber_len(len(value)) + value


def _ber_int(value: int, *, tag: int = 0x02) -> bytes:
    if value == 0:
        raw = b"\x00"
    else:
        raw = value.to_bytes((value.bit_length() + 7) // 8, "big", signed=False)
        if raw[0] & 0x80:
            raw = b"\x00" + raw
    return _ber_tlv(tag, raw)


def _ber_bool(value: bool) -> bytes:
    return _ber_tlv(0x01, b"\xff" if value else b"\x00")


def _ber_octet(value: str) -> bytes:
    return _ber_tlv(0x04, value.encode("utf-8"))


def _ber_enum(value: int) -> bytes:
    return _ber_int(value, tag=0x0A)


def _ber_seq(*items: bytes, tag: int = 0x30) -> bytes:
    return _ber_tlv(tag, b"".join(items))


def _ber_set(*items: bytes) -> bytes:
    return _ber_seq(*items, tag=0x31)


def _ber_app(app_tag: int, *items: bytes) -> bytes:
    return _ber_seq(*items, tag=0x60 + app_tag)


def _read_len(data: bytes, pos: int) -> tuple[int, int]:
    first = data[pos]
    pos += 1
    if not first & 0x80:
        return first, pos
    count = first & 0x7F
    return int.from_bytes(data[pos : pos + count], "big"), pos + count


def _read_tlv(data: bytes, pos: int = 0) -> tuple[int, bytes, int]:
    tag = data[pos]
    pos += 1
    length, pos = _read_len(data, pos)
    end = pos + length
    return tag, data[pos:end], end


def _int_from(value: bytes) -> int:
    return int.from_bytes(value, "big", signed=bool(value and value[0] & 0x80))


def _collect_octets(data: bytes) -> list[str]:
    values: list[str] = []
    pos = 0
    while pos < len(data):
        try:
            tag, value, pos = _read_tlv(data, pos)
        except (IndexError, ValueError):
            break
        if tag == 0x04:
            try:
                values.append(value.decode("utf-8"))
            except UnicodeDecodeError:
                continue
        elif tag & 0x20 or tag in {0x30, 0x31, 0xA0, 0xA3, 0x87}:
            values.extend(_collect_octets(value))
    return values


def _recv_message(sock: socket.socket) -> bytes | None:
    header = sock.recv(2)
    if not header:
        return None
    if len(header) < 2 or header[0] != 0x30:
        return None
    first_len = header[1]
    if not first_len & 0x80:
        length = first_len
        prefix = header
    else:
        count = first_len & 0x7F
        extra = sock.recv(count)
        if len(extra) != count:
            return None
        length = int.from_bytes(extra, "big")
        prefix = header + extra
    body = b""
    while len(body) < length:
        chunk = sock.recv(length - len(body))
        if not chunk:
            break
        body += chunk
    return prefix + body if len(body) == length else None


def _ldap_message(message_id: int, protocol_op: bytes) -> bytes:
    return _ber_seq(_ber_int(message_id), protocol_op)


def _bind_response(message_id: int, result_code: int = 0, diagnostic: str = "") -> bytes:
    return _ldap_message(message_id, _ber_app(1, _ber_enum(result_code), _ber_octet(""), _ber_octet(diagnostic)))


def _search_done(message_id: int, result_code: int = 0, diagnostic: str = "") -> bytes:
    return _ldap_message(message_id, _ber_app(5, _ber_enum(result_code), _ber_octet(""), _ber_octet(diagnostic)))


def _search_entry(message_id: int, entry: dict[str, Any]) -> bytes:
    attrs = []
    for name, values in entry["attributes"].items():
        attrs.append(_ber_seq(_ber_octet(name), _ber_set(*[_ber_octet(str(v)) for v in values])))
    return _ldap_message(message_id, _ber_app(4, _ber_octet(entry["dn"]), _ber_seq(*attrs)))


def _message_id_and_op(raw: bytes) -> tuple[int, int, bytes]:
    tag, value, _ = _read_tlv(raw, 0)
    if tag != 0x30:
        raise ValueError("LDAP message must be a sequence")
    id_tag, id_value, pos = _read_tlv(value, 0)
    if id_tag != 0x02:
        raise ValueError("LDAP message missing messageID")
    op_tag, op_value, _ = _read_tlv(value, pos)
    return _int_from(id_value), op_tag, op_value


def _search_entries(filter_text: str) -> list[dict[str, Any]]:
    query = (filter_text or "").strip().lower()
    if query in {"", "(objectclass=javanamingreference)", "(objectclass=*)"}:
        return [ldap_entry(name, binding) for name, binding in LDAP_BINDINGS.items()]
    return [
        ldap_entry(name, binding)
        for name, binding in LDAP_BINDINGS.items()
        if query in name.lower() or query in str(binding).lower()
    ]


class _LDAPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        while True:
            raw = _recv_message(self.request)
            if not raw:
                return
            try:
                message_id, op_tag, op_value = _message_id_and_op(raw)
            except ValueError:
                return
            if op_tag == 0x60:
                octets = _collect_octets(op_value)
                principal = octets[0] if octets else ""
                if principal.endswith(BASE_DN):
                    self.request.sendall(_bind_response(message_id))
                else:
                    self.request.sendall(_bind_response(message_id, 49, "invalidCredentials"))
            elif op_tag == 0x63:
                octets = _collect_octets(op_value)
                filter_text = octets[-1] if octets else ""
                for entry in _search_entries(filter_text):
                    self.request.sendall(_search_entry(message_id, entry))
                self.request.sendall(_search_done(message_id))
            else:
                self.request.sendall(_search_done(message_id, 53, f"unsupported operation tag {op_tag}"))


class _LDAPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@dataclass(frozen=True)
class LDAPRuntime:
    host: str
    port: int
    version: str = "controlled-ldap-runtime-v1"

    @property
    def endpoint(self) -> str:
        return f"ldap://{self.host}:{self.port}/{BASE_DN}"


_runtime_lock = threading.Lock()
_runtime: LDAPRuntime | None = None
_server: _LDAPServer | None = None


def ensure_ldap_runtime() -> LDAPRuntime:
    global _runtime, _server
    with _runtime_lock:
        if _runtime is not None:
            return _runtime
        host = os.getenv("LEGACY_LDAP_HOST", "127.0.0.1")
        preferred_port = int(os.getenv("LEGACY_LDAP_PORT", "1389"))
        try:
            server = _LDAPServer((host, preferred_port), _LDAPHandler)
        except OSError:
            server = _LDAPServer((host, 0), _LDAPHandler)
        thread = threading.Thread(target=server.serve_forever, name="controlled-ldap-runtime", daemon=True)
        thread.start()
        _server = server
        _runtime = LDAPRuntime(host=server.server_address[0], port=int(server.server_address[1]))
        return _runtime


def _send_ldap(messages: list[bytes], *, timeout: float = 5.0) -> list[tuple[int, int, bytes]]:
    runtime = ensure_ldap_runtime()
    responses: list[tuple[int, int, bytes]] = []
    with socket.create_connection((runtime.host, runtime.port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        for message in messages:
            sock.sendall(message)
            while True:
                raw = _recv_message(sock)
                if not raw:
                    break
                message_id, op_tag, op_value = _message_id_and_op(raw)
                responses.append((message_id, op_tag, op_value))
                if op_tag in {0x61, 0x65}:
                    break
    return responses


def _bind_request(message_id: int, principal: str, credential: str = "contoso-demo") -> bytes:
    return _ldap_message(
        message_id,
        _ber_app(0, _ber_int(3), _ber_octet(principal), _ber_tlv(0x80, credential.encode("utf-8"))),
    )


def _search_request(message_id: int, base_dn: str, filter_text: str) -> bytes:
    filter_value = filter_text or "(objectClass=javaNamingReference)"
    return _ldap_message(
        message_id,
        _ber_app(
            3,
            _ber_octet(base_dn),
            _ber_enum(2),
            _ber_enum(0),
            _ber_int(0),
            _ber_int(0),
            _ber_bool(False),
            _ber_tlv(0xA3, _ber_octet("objectClass") + _ber_octet(filter_value)),
            _ber_seq(),
        ),
    )


def _result_code(op_value: bytes) -> int:
    tag, value, _ = _read_tlv(op_value, 0)
    if tag != 0x0A:
        return -1
    return _int_from(value)


def ldap_bind(principal: str = DEFAULT_BIND_DN, credential: str = "contoso-demo") -> dict[str, Any]:
    runtime = ensure_ldap_runtime()
    responses = _send_ldap([_bind_request(1, principal, credential)])
    result_code = _result_code(responses[0][2]) if responses else -1
    return {
        "wire_protocol": "ldapv3",
        "runtime_mode": "ldap_runtime",
        "server": runtime.endpoint,
        "message_ids": [response[0] for response in responses],
        "principal": principal,
        "bound": result_code == 0,
        "result_code": result_code,
    }


def ldap_search(filter_text: str = "", *, base_dn: str = BASE_DN) -> dict[str, Any]:
    runtime = ensure_ldap_runtime()
    responses = _send_ldap([_bind_request(1, DEFAULT_BIND_DN), _search_request(2, base_dn, filter_text)])
    entries = []
    for _message_id, op_tag, op_value in responses:
        if op_tag == 0x64:
            octets = _collect_octets(op_value)
            if octets:
                dn = octets[0]
                match = next((entry for entry in _search_entries(filter_text) if entry["dn"] == dn), None)
                if match:
                    entries.append(match)
    done = [value for _message_id, op_tag, value in responses if op_tag == 0x65]
    result_code = _result_code(done[-1]) if done else -1
    return {
        "wire_protocol": "ldapv3",
        "runtime_mode": "ldap_runtime",
        "server": runtime.endpoint,
        "message_ids": [response[0] for response in responses],
        "base_dn": base_dn,
        "filter": filter_text or "(objectClass=javaNamingReference)",
        "entries": entries,
        "result_code": result_code,
        "searched": result_code == 0,
    }


def ldap_lookup(name: str) -> dict[str, Any]:
    search = ldap_search(name)
    binding = LDAP_BINDINGS.get(name)
    if binding is None:
        binding = {"type": "dynamic.lookup", "value": name, "dn": f"cn={name.replace('/', '_')},{BASE_DN}"}
    return {
        **search,
        "lookup_name": name,
        "binding": binding,
        "ldap_entry": ldap_entry(name, binding),
        "lookup_found": name in LDAP_BINDINGS,
    }
