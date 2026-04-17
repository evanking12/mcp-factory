# Architect Brief: 003 CORBA ORB Runtime

Decision:
- Use `jeteve-omniorb` in the Linux pipeline image to provide OmniORB and
  OmniORBpy without apt-level CORBA setup.

Why:
- The tranche requires a real ORB/IIOP proof, not the previous IDL-shaped object
  registry. The selected wheel packages OmniORB/OmniORBpy for CPython 3.10 on
  manylinux and keeps the proof deployable inside the existing ACA.
- Local Windows development cannot import the Linux wheel, so local tests only
  validate the fallback shape and command wiring. The authoritative gate is the
  deployed focused workflow.

Trust boundary:
- Allowed claim after workflow proof: controlled OmniORB/IIOP runtime proof for
  deterministic Contoso IDL.
- Disallowed claim: generalized CORBA estate migration, arbitrary ORB discovery,
  or production CORBA modernization.

Next blocker:
- Validate that the deployed ACA imports OmniORB, runs `omniidl`, exposes
  `provider_modes.corba=corba_orb_runtime`, and returns an IOR-backed client
  invocation before moving to MSRPC.
