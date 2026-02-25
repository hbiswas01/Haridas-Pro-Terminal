import streamlit as st
import streamlit.components.v1 as components
import datetime
import pytz
import yfinance as yf
import pandas as pd
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import os
import requests
import hmac
import hashlib
import json
import random  # <--- এই লাইনটি নতুন যোগ কর
