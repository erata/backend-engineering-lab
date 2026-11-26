#!/usr/bin/env python3
"""Runs the portable pure-Java subset with JDK 21+ (no external dependencies)."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'implementations/spring-boot/cache-core/src/main/java/de/backendlab/cache'
files = [str(p) for p in sorted(source.glob('*.java')) if p.name not in ('CaffeineCache.java', 'CacheFactory.java')]
with tempfile.TemporaryDirectory() as dest:
    subprocess.run(['javac', '--release', '21', '-d', dest, *files, str(ROOT/'tools/OfflineChecks.java')], check=True)
    subprocess.run(['java', '-cp', dest, 'de.backendlab.cache.OfflineChecks'], check=True)
