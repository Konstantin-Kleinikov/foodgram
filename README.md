[![Main Foodgram workflow](https://github.com/Konstantin-Kleinikov/foodgram/actions/workflows/main.yml/badge.svg)](https://github.com/Konstantin-Kleinikov/foodgram/actions/workflows/main.yml)
#  Социальная сеть для обмена рецептами приготовления еды Foodgram

Адрес сайта: https://yp-foodgram.zapto.org/

## Описание проекта

Данный проект представляет собой социальную сеть, которая позволяет пользователям: 
- публиковать свои рецепты 
- добавлять чужие рецепты в избранное 
- подписываться на публикации других авторов 
- зарегистрированным пользователям доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

## Использованные технологии
- Python — разработка backend, версия 3.9
- Django — веб-фреймворк, версия 4.2
- Django REST Framework — создание API, версия 3.16
- JavaScript — разработка frontend
- React — фреймворк для frontend
- Nginx — веб-сервер и обратный прокси
- Docker — контейнеризация и деплой
- PostgreSQL — база данных
- GitHub Actions — автоматизация CI/CD
- npm — управление пакетами frontend


## Как развернуть проект локально

### 1. Клонируйте репозиторий на компьютер

### 2. Заполните переменные окружения
Для корректной работы проекта необходимо заполнить переменные окружения. Создайте файл `.env` в 
корневой директории проекта и добавьте в него следующие переменные:

```env
- SECRET_KEY=your_django_secret_key
- DEBUG=True
- ALLOWED_HOSTS=your_domain.com,localhost,127.0.0.1
- DB_ENGINE=sqlite
- DB_NAME=your_db_name
- POSTGRES_USER=your_db_user
- POSTGRES_PASSWORD=your_db_password
- DB_HOST=db
- DB_PORT=5432
```
### 3. Установите зависимости и выполните миграции
В терминале перейдите в директорию backend и выполните следующие команды:

```python
pip install -r requirements.txt
python manage.py migrate
```
### 4. Запустите frontend-проект
```bash
npm run start
```
### 5. Запустите backend-проект
```bash
python manage.py runserver
```
### 6. Откройте в браузере адрес http://localhost:3000


## Как развернуть проект на удаленном сервере

### 1. Создайте каталог проекта
Зайдите на удаленный сервер и в директории /home/<user>/ создайте каталог foodgram.

### 2. Заполните переменные окружения
Для корректной работы проекта необходимо заполнить переменные окружения. Создайте файл `.env` в 
корневой директории проекта foodgram и добавьте в него следующие переменные:

```env
- SECRET_KEY=your_django_secret_key
- DEBUG=False
- ALLOWED_HOSTS=your_domain.com,localhost,127.0.0.1
- DB_ENGINE=postgres
- DB_NAME=your_db_name
- POSTGRES_USER=your_db_user
- POSTGRES_PASSWORD=your_db_password
- DB_HOST=db
- DB_PORT=5432
```
### 3. Заполните переменные Secrets в GitHub
В Settings проекта перейдите в Secrets and variables и зайдите на страницу Actions.
Заполните следующие Repository secrets:
```env
- DOCKER_USERNAME=your_docker_hub_username
- DOCKER_PASSWORD=your_docker_hub_password
- HOST=remote_server_host_ip
- USER=your_remote_server_user
- SSH_KEY=your_ssh_private_key
- SSH_PASSPHRASE=your_ssh_pass_phrase
```

### 4. Выполните push из локального сервера, чтобы запустился GitHub Action



## Автор проекта
[Константин Клейников](https://github.com/Konstantin-Kleinikov) в рамках обучения
на Яндекс.Практикум по программе Python-разработчик расширенный (когорта 57+).

