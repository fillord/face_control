// PM2 ecosystem config for face-recognition attendance system
//
// BEFORE APPLYING:
//   1. Generate a strong secret:
//      /var/www/sites/face-almgp33/venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
//   2. Replace REPLACE_WITH_GENERATED_SECRET below with the output.
//   3. Apply:
//      pm2 start /var/www/sites/face-almgp33/ecosystem.config.js
//      # or, if face-recognition already exists in PM2:
//      pm2 restart face-recognition --update-env
//   4. Verify:
//      pm2 status                     # shows face-recognition online
//      pm2 describe face-recognition  # confirm -w 1 in args
//
// Single worker (-w 1) is required — the JSON file store uses advisory
// fcntl.flock locking which protects against concurrent writes within
// the same process but is not safe across multiple gunicorn workers.

module.exports = {
  apps: [
    {
      name: "face-recognition",
      script: "/var/www/sites/face-almgp33/venv/bin/gunicorn",
      args: "-w 1 -b 127.0.0.1:5051 app:app",
      interpreter: "none",
      cwd: "/var/www/sites/face-almgp33",
      exec_mode: "fork",
      env: {
        // Replace this placeholder with the output of:
        // /var/www/sites/face-almgp33/venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
        SECRET_KEY: "REPLACE_WITH_GENERATED_SECRET"
      }
    }
  ]
};
