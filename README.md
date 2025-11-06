# petro-master

##
to run the server

```bash
python manage.py runserver
```

## to run the celery worker
```bash
celery -A config worker --loglevel=info
celery -A config worker --loglevel=info --purge
```

## to run the celery beat
```bash
celery -A config beat --loglevel=info
```
