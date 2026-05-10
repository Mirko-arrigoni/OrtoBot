default:
    echo 'Hello, world!'

# Starts the application
run:
	uv run src/main.py

# Deletes the log files
clean:
	echo "" > log.txt

format: fmt
fmt:
	uv run -m black --target-version py311 src/
