"""Compatibility entry point; the canonical Flask app is backend.app."""

import os

from backend.app import app, seed_data


if __name__ == "__main__":
    seed_data()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
