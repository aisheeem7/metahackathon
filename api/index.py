from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.app import app as flask_app

# Export for Vercel
app = flask_app
