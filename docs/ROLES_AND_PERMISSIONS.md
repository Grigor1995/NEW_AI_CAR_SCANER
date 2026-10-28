# Roles and permissions

| Capability | USER | CUSTOMER | ADMIN | MARKET |
|---|---|---|---|---|
| Own local profile, vehicles, preferences | yes | yes | yes | inherits primary role |
| Select primary mode | assigned only | assigned only | assigned only | never a primary mode |
| Modify role assignments over HTTP | no | no | no endpoint yet | no |
| Inspect another owner vehicle | no | requires future explicit consent | no universal bypass | no |
| ECU write | locked | locked pending verified executor | locked | no |
| Merchant/workshop/admin business operations | planned | planned | planned | planned |

New registrations receive USER only. Customer/admin/merchant assignments are made by an explicit local operator CLI against a controlled database, never trusted from registration JSON. Every authenticated HTTP call rechecks active account, role state and token expiry in storage. Token logout immediately revokes that token. No password/contact verification or remote provisioning workflow is fabricated.
