<h2>Configuration de richcorp</h2>

Cette partie du README explique comment configurer et exécuter notre projet Django dans les environnements de développement et de production.

<h3>Structure du Projet</h3>

```
richcorp/
├── settings_conf/
│   ├── __init__.py
│   ├── base.py
│   ├── local.py
│   └── production.py
├── asgi.py
├── wsgi.py
└── ...
manage.py
```

<h3>Configuration de l'Environnement</h3>

<h4>1. Environnement Virtuel</h4>

Créez et activez un environnement virtuel :

```bash
python -m venv venv
source venv/bin/activate  # Sur Unix ou MacOS
venv\Scripts\activate     # Sur Windows
```

<h4>2. Installation des Dépendances</h4>

```bash
pip install -r requirements.txt
```

<h4>3. Variables d'Environnement</h4>

Créez un fichier `.env` à la racine du projet et ajoutez les variables nécessaires :

```
SECRET_KEY=votre_cle_secrete
DEBUG=True  # En développement, False en production
DATABASE_URL=sqlite:///db.sqlite3  # Exemple pour SQLite
```

<h3>Exécution en Développement</h3>

1. Assurez-vous que `manage.py` utilise les paramètres locaux :

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'richcorp.settings_conf.local')

# or 

export DJANGO_SETTINGS_MODULE='richcorp.settings_conf.local'
```

2. Appliquez les migrations :

```bash
python manage.py migrate
```

3. Lancez le serveur de développement :

```bash
python manage.py runserver
```

L'application sera accessible à `http://127.0.0.1:8000`

<h3>Exécution en Production</h3>

1. Modifiez `manage.py` pour utiliser les paramètres de production :

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'richcorp.settings_conf.production')

# or 

export DJANGO_SETTINGS_MODULE='richcorp.settings_conf.production'

```

2. Collectez les fichiers statiques :

```bash
python manage.py collectstatic
```

3. Appliquez les migrations :

```bash
python manage.py migrate
```

4. Utilisez Gunicorn pour WSGI et Daphne pour ASGI :

```bash
gunicorn richcorp.wsgi:application
daphne richcorp.asgi:application
```

5. Configurez Nginx comme proxy inverse et pour servir les fichiers statiques.

6. Utilisez Supervisor pour gérer les processus.

<h3>Utilisation des Variables d'Environnement</h3>

Pour basculer entre les environnements :

```bash
export DJANGO_SETTINGS_MODULE=parameter.settings_conf.production
# ou
export DJANGO_SETTINGS_MODULE=richcorp.settings_conf.local
```

Dans `manage.py` et `wsgi.py` :

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_SETTINGS_MODULE', 'richcorp.settings_conf.local'))
```

<h3>Commandes Utiles</h3>

- Créer un superutilisateur : `python manage.py createsuperuser`
- Lancer les tests : `python manage.py test`
- Vérifier les migrations : `python manage.py showmigrations`


# 5BSS API

### Installation steps

## Ensure you have python3 installed
#### version python 3.9.7

1. Ensure you have python3 installed

2. Clone the repository
3. create a virtual environment using `virtualenv venv`
4. Activate the virtual environment by running `source venv/bin/activate`

- On Windows use `source venv\Scripts\activate`

5. Install the dependencies using `pip install -r requirements.txt`

6. Migrate existing db tables by running `python manage.py migrate`

7. Run the django development server using `python manage.py runserver`



# Demarer celery 
## celery worker
celery -A parameter worker --loglevel=INFO --pool=solo

## celery beat

celery -A parameter beat -l info# VisoCard


## generator data

# si ton tenant 'ecide' est le défaut, simplement :
python manage.py seed_programmes

# ou choix explicite :
python manage.py seed_programmes --schema=ecide

python manage.py seed_news --schema=tenant2





# RichCorporation
