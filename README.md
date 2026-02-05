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


<!-- Model generate django  -->

pip install django-extensions graphviz


Je te montre 2 méthodes :

✅ Méthode 1 (la plus pro) : génération automatique UML depuis Django avec Graphviz

✅ Méthode 2 (facile à partager) : diagramme Mermaid (copier-coller dans GitHub/Notion)

✅ Méthode 1 — Générer UML automatiquement (Django → Graphviz)
1) Installer les outils

Dans ton venv :

pip install django-extensions graphviz

Installer Graphviz sur macOS
brew install graphviz

2) Ajouter dans INSTALLED_APPS

Dans config/settings/base.py :

INSTALLED_APPS = [
    # ...
    "django_extensions",
    # tes apps
    "apps.abc_apps.accounts",
    "apps.abc_apps.academics",
    "apps.abc_apps.sessions_abc",
    "apps.abc_apps.attendance",
    "apps.abc_apps.exams",
    "apps.abc_apps.speeches",
    "apps.abc_apps.news",
    "apps.abc_apps.feedback",
    "apps.abc_apps.gate_security",
    "apps.abc_apps.access_control",
]

3) Générer le diagramme UML (image)

Tu peux générer un diagramme complet :

python manage.py graph_models \
  accounts academics sessions_abc attendance exams speeches news feedback gate_security access_control \
  -a -g -o abc_models.png


✅ Résultat : abc_models.png avec toutes les classes et relations (FK/OneToOne/ManyToMany)

Tu peux aussi générer en PDF :

python manage.py graph_models \
  accounts academics sessions_abc attendance exams speeches news feedback gate_security access_control \
  -a -g -o abc_models.pdf

4) Si ton diagramme est trop grand (astuce)

Génère par modules :

python manage.py graph_models accounts -a -g -o uml_accounts.png
python manage.py graph_models academics sessions_abc -a -g -o uml_sessions.png
python manage.py graph_models attendance exams -a -g -o uml_attendance_exams.png
python manage.py graph_models speeches news feedback -a -g -o uml_content.png
python manage.py graph_models gate_security access_control -a -g -o uml_security_access.png

✅ Méthode 2 — Diagramme Mermaid (copier-coller)

Tu peux coller ce diagramme dans un fichier docs/uml.md sur GitHub.

Il résume les relations principales (pas chaque champ), mais c’est clair.

Diagram
classDiagram

class User {
  +role
}
class StudentProfile
class TeacherProfile

User "1" --> "0..1" StudentProfile
User "1" --> "0..1" TeacherProfile

class ClassRoom
class Course
class TeacherCourseAssignment
class MonthlyGoal

TeacherProfile "1" --> "0..*" TeacherCourseAssignment
ClassRoom "1" --> "0..*" TeacherCourseAssignment
Course "1" --> "0..*" TeacherCourseAssignment
ClassRoom "1" --> "0..*" MonthlyGoal

class ClassSession
class SessionTeacher
class AttendanceToken

ClassRoom "1" --> "0..*" ClassSession
ClassSession "1" --> "0..*" SessionTeacher
TeacherProfile "1" --> "0..*" SessionTeacher
ClassSession "1" --> "0..1" AttendanceToken

class StudentAttendance
class TeacherCheckIn
class AttendanceConfirmation

ClassSession "1" --> "0..*" StudentAttendance
StudentProfile "1" --> "0..*" StudentAttendance

ClassSession "1" --> "0..*" TeacherCheckIn
TeacherProfile "1" --> "0..*" TeacherCheckIn

ClassSession "1" --> "0..*" AttendanceConfirmation
TeacherProfile "1" --> "0..*" AttendanceConfirmation

class ExamRuleStatus
class ExamEntryScan
class MonthlyReturnForm

StudentProfile "1" --> "0..*" ExamRuleStatus
ClassRoom "1" --> "0..*" ExamRuleStatus

ClassSession "1" --> "0..*" ExamEntryScan
StudentProfile "1" --> "0..*" ExamEntryScan

StudentProfile "1" --> "0..*" MonthlyReturnForm

class Speech
class SpeechCorrection
class SpeechCoaching
class SpeechScore
class SpeechPublicationDecision

StudentProfile "1" --> "0..*" Speech
Speech "1" --> "0..1" SpeechCorrection
Speech "1" --> "0..1" SpeechCoaching
Speech "1" --> "0..*" SpeechScore
Speech "1" --> "0..1" SpeechPublicationDecision
TeacherProfile "1" --> "0..*" SpeechScore

class NewsPost
User "1" --> "0..*" NewsPost

class TeacherRemark
class MonthlyStudentReport
StudentProfile "1" --> "0..*" TeacherRemark
TeacherProfile "1" --> "0..*" TeacherRemark
StudentProfile "1" --> "0..*" MonthlyStudentReport

class GateEntry
User "0..1" --> "0..*" GateEntry

class Credential
class AccessPoint
class AccessRule
class AccessLog

User "1" --> "0..*" Credential
ClassRoom "0..1" --> "0..*" AccessPoint
AccessPoint "1" --> "0..*" AccessRule
AccessPoint "1" --> "0..*" AccessLog
User "0..1" --> "0..*" AccessLog
GateEntry "0..1" --> "0..*" AccessLog

✅ Le plus important: la commande exacte pour toi


python manage.py graph_models \
  accounts academics sessions_abc attendance exams speeches news feedback gate_security access_control \
  -a -g -o abc_models.png

CommandError: Neither pygraphviz nor pydotplus could be found to generate the image. To generate text output, use the --json or --dot options.
(venv) achille@192 Rich Corporation % brew install graphviz
pip install pygraphviz

✔︎ JSON API formula.jws.json                                                          Downloaded   32.0MB/ 32.0MB
✔︎ JSON API cask.jws.json                                                             Downloaded   15.3MB/ 15.3MB
Warning: graphviz 14.1.2 is already installed and up-to-date.
To reinstall 14.1.2, run:
  brew reinstall graphviz
Collecting pygraphviz
  Downloading pygraphviz-1.11.zip (120 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Building wheels for collected packages: pygraphviz
  Building wheel for pygraphviz (pyproject.toml) ... done
  Created wheel for pygraphviz: filename=pygraphviz-1.11-cp39-cp39-macosx_13_0_x86_64.whl size=101910 sha256=1c8ee789d3421d30dd6fa89cfc0b66ede846ca66c833fd75b5e54aae1c85ec86
  Stored in directory: /Users/achille/Library/Caches/pip/wheels/2a/15/84/0cfa4492795c389d89e0c3101f6d42e6201a66869a9c8b576e
Successfully built pygraphviz
Installing collected packages: pygraphviz
Successfully installed pygraphviz-1.11
(venv) achille@192 Rich Corporation % python manage.py graph_models \
  accounts academics sessions_abc attendance exams speeches news feedback gate_security access_control \
  -a --dot -o abc_models.dot

(venv) achille@192 Rich Corporation % dot -Tpng abc_models.dot -o abc_models.png

(venv) achille@192 Rich Corporation % 