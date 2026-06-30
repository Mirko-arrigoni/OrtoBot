# Starts the application
run:
	uv run src/main.py

# Deletes the log files
clean:
	echo "" > log.txt

format: fmt
fmt:
	uv run -m black --target-version py313 src/

# Run program in debug mode
debug:
    uv run python -m debugpy --listen 0.0.0.0:5678 --wait-for-client src/main.py

# Stop program manually
stop:
    pkill -f main.py
