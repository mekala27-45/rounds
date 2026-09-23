"""Strict schema and identifier gate for the limited private demo payload."""
import json,re

PATTERNS=[re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',re.I),re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',re.I)]
ALLOWED={'id','age_band','sex','index_admission','observation_end','conditions','timeline','labs'}
def validate_private_payload(payload):
 if not isinstance(payload,dict) or not payload.get('patients'): raise ValueError('A nonempty patient payload is required.')
 if len(payload['patients'])>60: raise ValueError('Patient payload exceeds its limit.')
 for p in payload['patients']:
  if set(p)!=ALLOWED: raise ValueError('Patient fields fail the allowlist.')
  if not re.fullmatch('[0-9a-f]{20}',p['id']): raise ValueError('Patient ID is not a permitted pseudonym.')
  if len(p['timeline'])>10 or len(p['labs'])>10: raise ValueError('Timeline exceeds its limit.')
 text=json.dumps(payload)
 if any(pattern.search(text) for pattern in PATTERNS): raise ValueError('An identifier pattern survived the privacy gate.')
 return True
