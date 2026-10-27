# Add this foundation without breaking the current deployment

1. Download and extract this ZIP on your computer.
2. Open `https://github.com/bramwelpaule4-dot/timan-intelligence`.
3. Before changing anything, confirm `app.py` is still present and the Streamlit app currently works.
4. Add the new files/folders from this package to the repository. **Do not replace or delete `app.py`.**
5. If `requirements.txt` already exists or has extra dependencies, merge the listed dependencies into it rather than blindly replacing it.
6. Commit with a message such as `Add modular analytics foundation`.
7. Wait for Streamlit Community Cloud to redeploy, then open the live app and verify its existing pages still work.
8. The new package is intentionally not imported by the existing `app.py` yet. The first deployment should be an additive, low-risk architecture commit.
9. After that deployment is verified, we can migrate one existing feature at a time and run the included tests.

## Important

- Keep `.streamlit/secrets.toml`, `.env`, API keys, real household survey data and confidential client files out of GitHub.
- `requirements-desktop.txt` is for local desktop development; Streamlit Cloud should continue using root `requirements.txt`.
- The desktop launcher is a shell only. It is not yet a finished desktop application.
