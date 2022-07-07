# Weather
The app allows a user to log in or register and check the weather for a chosen city. To do so it utilises:

-**FastApi** - returning prepared **HTML** templates with **Jinja2Templates**

-**PostgreSQL** - storing user data (login, hashed password, last visited city), accessed using **SQLAlchemy ORM** with **Psycopg2** driver

-**Redis** - storing *token* (key) and *username* (value) for logged users

The app is wrapped in **Docker-Compose**, using official docker images for *postgreSQL* and *redis* and building a custom container image for the backend, specified in *Dockerfile*.

![obraz](https://user-images.githubusercontent.com/102622810/177599751-bcae634b-9541-43fc-8caa-8094221b0a70.png)

### Functionalities
-*Log In* - If the login and password (read with **OAuth2PasswordRequestForm**, verified using **PassLib CryptContext**) is found in *postgreSQL* database using *SQLAlchemy ORM session* , a *token* is created and entered into a *redis* database, with 1h expiry time, along with the user's *username*. Then, the token is set as a *cookie* and the user is redirected to the */weather* endpoint where the weather for the last checked city is displayed

-*Register* - If the entered login is not found in *postgreSQL* database, a new user is created and the user is logged in analogically with Poznań used as a default city. The password is hashed using *PassLib CryptContext* before insertion to the *postgreSQL* database

-*Check Weather* - A logged user can access the */weather* endpoint to display the weather, temperature, humidity and pressure for a chosen city. Data is fetched using an OpenWeatherMap API (http://api.openweathermap.org). The user can change the city using a form on the *HTML* page

-*Log Out* - Upon clicking the button, user's cookie *token* is deleted and the user is redirected to the root page.
