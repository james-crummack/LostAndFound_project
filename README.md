# 🚂 Lost & Found Management System

A polyglot persistence web application designed for managing lost and found items across a transport network. This project demonstrates the integration of **MySQL** (RDBMS) and **MongoDB** (NoSQL) with **Flask** as the backend framework. It includes full **RBAC (Role-Based Access Control)**, CRUD operations, and SQL/NoSQL interoperability.

---

## 📚 Features

- 🧑‍💼 **Role-Based Access Control (RBAC)**: Admin, Employee, and User roles with dynamic permissions.
- 🗄️ **CRUD Support**: Perform Create, Read, Update, Delete operations across SQL and MongoDB.
- 🧾 **Polyglot Persistence**: Combines the structure of MySQL with the flexibility of MongoDB.
- 📥 **Data Export**: Query results can be downloaded as CSV.
- 🎨 **Bootstrap-styled UI**: Clean, dark-mode interface for a better UX.

---

## 🔧 Technologies Used

- **Backend**: Python (Flask)
- **Databases**: MySQL, MongoDB
- **Frontend**: HTML, Bootstrap
- **Other**: Jinja2 templating, CSV export

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/lost-and-found-system.git
cd lost-and-found-system
```

### 2. Set up the environment
```python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```


### Start the application
```python app.py```


## 👤Demo Accounts

**Role**	          **Email**	              **Password**
Admin	      admin@example.com	      admin123
Employee	  employee@example.com	  emp123
User	      user@example.com	       user123

## Project Background
This project was developed as part of the BEMM459 module at the University of Exeter. It aims to showcase how polyglot persistence can solve real-world business problems by combining relational and non-relational data strategies in a single cohesive system.
