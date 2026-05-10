default:
    echo 'Hello, world!'

# Starts the application
run:
	uv run src/main.py

# Deletes the log files
clean:
	echo "DO SOMETHING"

format: fmt
fmt:
	uv run -m black --target-version py311 src/
