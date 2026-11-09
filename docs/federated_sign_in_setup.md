# TimanStat federated sign-in setup

TimanStat uses Streamlit's OpenID Connect (OIDC) support for Google and
Microsoft Entra ID. The identity provider authenticates the person; TimanStat
continues to load the account role, active status, MFA settings and session
version from its own database.

## Required Streamlit version

The web extra installs Streamlit with its authentication dependencies:

```bash
pip install -e ".[web]"
```

## Redirect URI

For the current development deployment, register this exact redirect URI
with each identity provider:

`https://timanstat-dev.streamlit.app/oauth2callback`

For another deployment domain, use that domain with the same
`/oauth2callback` path. The redirect URI must match exactly.

## Streamlit Community Cloud secrets

Add the following structure to the app's Streamlit Secrets. Replace every
placeholder with a value issued by the relevant provider. Generate a strong,
random `cookie_secret`; never commit real secrets to GitHub.

```toml
[auth]
redirect_uri = "https://timanstat-dev.streamlit.app/oauth2callback"
cookie_secret = "REPLACE_WITH_A_LONG_RANDOM_SECRET"

[auth.google]
client_id = "GOOGLE_CLIENT_ID"
client_secret = "GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[auth.microsoft]
client_id = "MICROSOFT_APPLICATION_CLIENT_ID"
client_secret = "MICROSOFT_CLIENT_SECRET"
server_metadata_url = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
```

Only a provider with all three provider-specific values configured is shown
on the sign-in page. Remove a provider's section to hide its sign-in option.

## Google setup

1. Open Google Cloud Console and create or select a project.
2. Configure the OAuth consent screen and publish/authorize the app as
   appropriate for the intended testers.
3. Create an OAuth client ID of type **Web application**.
4. Add the redirect URI above under **Authorized redirect URIs**.
5. Copy the client ID and client secret into the Google secrets section.

Google sign-in is accepted only when Google supplies an explicit
`email_verified = true` claim.

## Microsoft setup

1. Open Microsoft Entra admin center and register a new application.
2. Choose the account types TimanStat should support. For both personal
   Microsoft accounts and work/school accounts, use the supported
   multitenant-and-personal-account option.
3. Add a **Web** platform redirect URI using the exact URI above.
4. Create a client secret and copy its value immediately.
5. Copy the Application (client) ID and secret into Streamlit Secrets.

**Email verification safeguard:** Microsoft does not guarantee that every
OIDC response includes an `email_verified = true` claim. TimanStat currently
requires that explicit claim before it creates or links an account. A
Microsoft identity without that claim is rejected rather than being linked
to an account using an unverified email address. If this affects the intended
Microsoft tenants, the next implementation should add an authenticated
account-linking flow rather than weakening this check.

## Security behaviour

- New federated accounts are created with the standard `user` role.
- Existing accounts are linked only when the provider asserts a verified
  email matching an already verified TimanStat account.
- Provider subject IDs identify returning users; email is not the permanent
  provider identifier.
- Inactive or unverified TimanStat accounts are rejected.
- Existing TimanStat TOTP is still required after provider authentication.
- Password hashes are not populated with a usable password for federated-only
  accounts; email/password login remains available to existing password users.
- Sign-out clears the TimanStat session and the Streamlit OIDC identity cookie.

Do not expose client secrets, the OIDC cookie secret, ID tokens or access
tokens in the UI, logs, screenshots or source control.
