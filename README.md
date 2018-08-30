# Car catalog App 
-----------------------
This is a simple Car Catalog app programmed up using python and flask framework.

## Requirments
python version 3 ( Can be download from [here](https://www.python.org/downloads/))
virtual Environment.

## DataBase
DataBase ( named **carmodel** ) includes three tables:
* **Manager** table includes information about the Manager of a specific Brand
 ```
 id (type: integer) Primary Key
 name (type: text) not null
 email (type: text) not null
 picture (type: text)
 ```


* **Brand** table includes the Brand
 ```
 id (type: integer) Primary Key
 name (type: text) not null
 manager_id (type: integer) Foregin key =>(Manager.id)
 ```
* **Model** table includes all models
 ```
 id (type: integer) Primary Key
 name (type: text) not null
 description (type: text) not null
 price (type: integer) not null
 brand_id (type: integer) Foregin key =>(Brandr.id)
 manager_id (type: integer) Foregin key =>(Manager.id)
 ```

## Installation
download or Clone the GitHub repository

https://github.com/Basheer88/carcatalog.git

# Files of the repository
project file : run this file to make the app working then access the app using (localhost:8000)
database_setup : to generate an empty database
addone : this will add one entry for the empty database. can be used to help you understand how to add entry to the database.

# License
Free license. Feel free to do whatever you want with it.