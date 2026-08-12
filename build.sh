echo "Installing requirements..."
python3 -m pip install -r requirements.txt

echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Running migrations..."
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput