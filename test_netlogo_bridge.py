import sys
print("Using Python:", sys.executable)

from netlogo_bridge import run_once, close

if __name__ == "__main__":
    results = run_once(steps=100, sheep_init=80, wolves_init=50)
    print("Simulation results after 100 steps:")
    print(results)
    close()
