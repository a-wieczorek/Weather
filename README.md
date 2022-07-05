# Weather
The app allows a user to log in or register and check the weather for a chosen city. To do so it utilises:

-**FastApi** - backend

-**PostgreSQL** - storing user data (login, hashed password, last visited ('default') city)

-**Redis** - storing *token* (key) and *username* (value) for logged users

### Functionalities
-*Log In* - If the login and password (read with **OAuth2PasswordRequestForm**, hashed and verified using **PassLib CryptContext**) is found in database using *postgreSQL*, a *token* is created and entered into a *redis* database, with 1h expiry time, along with the user's *username*. Then, it is set as a *cookie* and the user is redirected to the */weather* endpoint where the weather for the last checked city is displayed

-*Register* - If the entered login is not found in 'postgreSQL* database, a new user is created and the user is logged in analogically with Poznań used as a default city.

-*Check Weather* - A logged user can access the */weather* endpoint to display the weather, temperature, humidity and pressure for a chosen city. Data is fetched using an OpenWeatherMap API 'http://api.openweathermap.org'. The user can change the city using a form in the **HTML**

-*Log Out* - Upon clicking the button, user's cookie *token* is deleted and the user is redirected to the root page.
