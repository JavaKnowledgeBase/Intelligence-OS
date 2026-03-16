# Developer: Ravi Kafley
# Seed identities for the starter auth flow until a real user store is added.
# Passwords are stored as scrypt-derived hash records, not plaintext.
AUTH_USERS = [
    {
        "id": "user-ravi-kafley",
        "email": "founder@example.com",
        "password_hash": "1ab87fab39c08e0a949862e0c4de6d4a:88f199e66b18d831a7d71aa95bc5d5f8910ed0731df24b1139d2f838c82ac6ed3720fa6a63f2bad13eddacc51476a830b642ea1c108e6a5ee2b8922229682ffe",
        "full_name": "Ravi Kafley",
        "role": "admin",
        "tenant_id": "tenant-torilaure",
    },
    {
        "id": "user-analyst-demo",
        "email": "analyst@example.com",
        "password_hash": "82b4b27814b1418a3bce4104a2fe421a:d4fd8c3f29f18547c25e138e98cf05c343a2ab6e576a9312e3ac559a35c3c9d9ae1b47ee25a1fe52a405fc9085412e4453fadb6eed6d6b5926313542102f5e61",
        "full_name": "Analyst Demo",
        "role": "analyst",
        "tenant_id": "tenant-torilaure",
    },
    {
        "id": "user-investor-demo",
        "email": "investor@example.com",
        "password_hash": "82b4b27814b1418a3bce4104a2fe421a:d4fd8c3f29f18547c25e138e98cf05c343a2ab6e576a9312e3ac559a35c3c9d9ae1b47ee25a1fe52a405fc9085412e4453fadb6eed6d6b5926313542102f5e61",
        "full_name": "Investor Demo",
        "role": "investor",
        "tenant_id": "tenant-torilaure",
    },
    {
        "id": "user-northstar-admin",
        "email": "admin@example.org",
        "password_hash": "1ab87fab39c08e0a949862e0c4de6d4a:88f199e66b18d831a7d71aa95bc5d5f8910ed0731df24b1139d2f838c82ac6ed3720fa6a63f2bad13eddacc51476a830b642ea1c108e6a5ee2b8922229682ffe",
        "full_name": "Northstar Admin",
        "role": "admin",
        "tenant_id": "tenant-northstar",
    },
]
