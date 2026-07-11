"""
Deploys the Meeting Follow-Up Automator as a Beam Pod running Streamlit.

Before running this:
  1. Install the Beam SDK/CLI and authenticate: `pip install beam-client && beam config create`
     (see https://docs.beam.cloud/getting-started/quickstart)
  2. (Optional, for one-click sending) Create Beam secrets so the app doesn't
     need credentials typed into the UI every time:
         beam secret create SLACK_WEBHOOK_URL https://hooks.slack.com/services/...
         beam secret create SMTP_USER you@example.com
         beam secret create SMTP_PASSWORD your-app-password
     Then run: `python start_server.py`

This mirrors Beam's own Streamlit example (docs.beam.cloud/v2/examples/streamlit),
with the app's actual dependencies and secrets wired in.
"""

from beam import Image, Pod

streamlit_server = Pod(
    image=Image().add_python_packages([
        "streamlit==1.41.1",
        "requests",
    ]),
    ports=[8501],  # Default port for streamlit
    cpu=2,
    memory=2048,
    entrypoint=["streamlit", "run", "app.py"],
    # Makes any secrets created via `beam secret create` available as env
    # vars inside the container (see app.py, which reads them via os.environ).
    # Remove any you haven't created, or Beam may fail to resolve them.
    secrets=["SLACK_WEBHOOK_URL", "SMTP_USER", "SMTP_PASSWORD"],
)

res = streamlit_server.create()

print("Streamlit server hosted at:", res.url)