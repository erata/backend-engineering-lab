from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as d:
 subprocess.run(['javac','--release','17','-d',d,str(r/'implementations/spring-boot/cache-core/src/main/java/de/backendlab/experiments/Experiments.java'),str(r/'tools/ExtendedChecks.java')],check=True)
 subprocess.run(['java','-cp',d,'ExtendedChecks'],check=True)
