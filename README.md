# ⚙️ PCbuild— Backend API

### FastAPI Backend for the ThriftBuild PC Building Platform

This repository contains the **backend API of ThriftBuild**, a PC hardware marketplace and AI-assisted PC configuration platform.

The backend is responsible for:

* REST API services
* Product management
* User management
* Order management
* Database communication
* Retailer data scraping
* Product filtering
* PC building support
* AI-assisted configuration
* Administrative operations

💻 **Frontend Repository:** https://github.com/Sanzid-Ahmed/PC_Build

🌐 **Live Website:** https://pc-build-ten.vercel.app/

---

# ✨ Features

## 👤 User Management

The backend provides APIs for managing application users.

Supported operations include:

* Create user
* Retrieve user
* Retrieve all users
* Search user by Firebase ID
* Search user by email
* Update user
* Delete user
* Check duplicate email
* Manage user roles
* Manage build limits

---

# 🛒 Product Management

The backend manages the centralized PC hardware catalog.

Each product can contain information such as:

* Product ID
* Store
* Product name
* Category
* Brand
* Product code
* Current price
* Previous price
* Status
* Warranty
* Rating
* Reviews
* Product URL
* Images
* Features
* Specifications
* Scraping timestamp

---

# 🔍 Product Filtering

The API supports filtering products according to different criteria.

### Category

```text
category
```

### Brand

```text
brand
```

### Store

```text
store
```

Multiple filters can also be combined.

```text
category + brand + store
```

---

# 🏪 Retailer Data Scraping

The backend includes a web-scraping system for collecting product information from hardware retailers.

The scraping pipeline can be represented as:

```text
Retailer Website
       ↓
BeautifulSoup
       ↓
Data Extraction
       ↓
Data Processing
       ↓
MySQL Database
       ↓
FastAPI API
       ↓
React Frontend
```

The collected data can include:

* Product names
* Prices
* Retailer
* Category
* Brand
* Images
* Product URLs
* Specifications
* Ratings
* Reviews

---

# 🤖 AI-Assisted PC Building

The backend supports the AI-assisted PC configuration workflow.

The frontend provides information such as:

* PC type
* Budget
* Preferences
* Requirements

The backend processes the configuration request and supports the generation of a suitable hardware configuration.

Supported workload categories include:

* Gaming
* Professional
* AI & ML
* Content Creation
* General Use

---

# 🧩 Custom PC Builder Support

The backend provides product data required by the Custom PC Builder.

Supported component categories include:

```text
CPU
Motherboard
RAM
GPU
Storage
PSU
Case
```

The API allows the frontend to retrieve relevant hardware and apply filtering based on configuration requirements.

---

# 📦 Order Management

The backend manages the customer order lifecycle.

### Order Creation

A new order stores information such as:

* User
* Firebase user ID
* Order status
* Creation time

### Order Products

Each order can contain multiple products.

The system stores:

* Product ID
* Product price at purchase
* Quantity

---

# 🔄 Order Lifecycle

Orders follow the following status flow:

```text
Pending
   ↓
Accepted
   ↓
On the Way
   ↓
Complete
```

Administrators can update the order status through the API.

---

# 👨‍💼 Administrative APIs

The backend supports administrative order management.

Administrators can:

* Retrieve all orders
* Retrieve individual orders
* Inspect customer information
* Inspect order products
* Update order status
* Delete orders

---

# 🗄️ Database

The backend uses **MySQL** for application data.

The primary database entities are:

```text
Users
Products
Orders
Order_Products
```

### Relationship

```text
Users
  │
  │ 1 : N
  ▼
Orders
  │
  │ 1 : N
  ▼
Order_Products
  │
  │ N : 1
  ▼
Products
```

---

# 📊 Database Tables

## `users`

```text
id
firebase_id
email
name
role
build_limit
created_at
```

---

## `products`

```text
id
store
name
category
brand
product_code
price
old_price
status
warranty
rating
reviews
url
images
features
specifications
scraped_at
```

---

## `orders`

```text
order_id
user_id
user_firebase_id
status
created_at
```

---

## `order_products`

```text
order_id
product_id
product_price
quantity
```

The `order_products` table acts as the associative entity between orders and products.

---

# 🔐 Firebase Integration

Firebase Authentication is used for user authentication.

The backend stores the Firebase user identifier in the database so that authenticated Firebase users can be associated with application-specific user records.

```text
Firebase Authentication
          ↓
      Firebase UID
          ↓
       FastAPI
          ↓
        MySQL
```

---

# 🏗️ Backend Architecture

```text
                         ┌─────────────────┐
                         │ React Frontend  │
                         └────────┬────────┘
                                  │
                             REST API
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    FastAPI      │
                         │     Backend     │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
        ┌───────────┐      ┌────────────┐      ┌────────────┐
        │   MySQL   │      │  Scraping  │      │ AI / Build │
        │ Database  │      │  System    │      │   Logic    │
        └───────────┘      └────────────┘      └────────────┘
```

---

# 🛠️ Technology Stack

| Technology    | Purpose                    |
| ------------- | -------------------------- |
| Python        | Backend programming        |
| FastAPI       | REST API framework         |
| Uvicorn       | ASGI server                |
| MySQL         | Database                   |
| BeautifulSoup | Web scraping               |
| Firebase      | Authentication integration |
| REST API      | Frontend communication     |

---

# 📂 Project Structure

A simplified structure:

```text
pc-builder-api/
│
├── app/
│   ├── main.py
│   ├── routers/
│   ├── database/
│   ├── models/
│   └── ...
│
├── requirements.txt
├── .env
└── README.md
```

> The exact structure may evolve during development.

---

# 🚀 Getting Started

## Prerequisites

Install:

* Python 3.x
* MySQL
* Git
* pip

---

## 1. Clone Repository

```bash
git clone https://github.com/Sanzid-Ahmed/pc-builder-api.git
```

---

## 2. Enter Directory

```bash
cd pc-builder-api
```

---

## 3. Create Virtual Environment

```bash
python -m venv venv
```

---

## 4. Activate Virtual Environment

### Windows CMD

```bash
venv\Scripts\activate
```

### Windows PowerShell

```bash
venv\Scripts\Activate.ps1
```

### Git Bash

```bash
source venv/Scripts/activate
```

---

## 5. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Create a `.env` file containing the required backend configuration.

Example:

```env
DATABASE_HOST=
DATABASE_PORT=
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_NAME=

FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=

AI_API_KEY=
```

> Use the exact environment variable names required by the implementation. Never commit `.env` files or private credentials to GitHub.

---

# ▶️ Run the Backend

Start the FastAPI development server using:

```bash
uvicorn app.main:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

---

# 📚 API Documentation

FastAPI automatically generates interactive API documentation.

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### ReDoc

```text
http://127.0.0.1:8000/redoc
```

Swagger UI can be used to test API endpoints directly from the browser.

---

# 🔌 API Functionality

The backend provides API functionality for:

### Users

```text
Create User
Get User
Get All Users
Update User
Delete User
```

### Products

```text
Get Products
Get Product
Filter by Category
Filter by Brand
Filter by Store
Get Categories
Get Brands
Get Stores
```

### Orders

```text
Create Order
Get User Orders
Get All Orders
Get Order Details
Update Order Status
Delete Order
```

---

# 🧠 Data Processing Pipeline

The backend combines API services, database operations, and web scraping.

```text
                    Retailer Websites
                           │
                           ▼
                    Web Scraping
                           │
                           ▼
                    Data Processing
                           │
                           ▼
                      MySQL DB
                           │
                           ▼
                       FastAPI
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                Frontend       AI Builder
```

---

# ⚠️ Current Limitations

### Scraping Dependency

Product data depends on external retailer websites and their page structures.

Changes to retailer websites may require updates to scraping logic.

### Data Synchronization

Retailer price and availability changes may not immediately appear in the database.

### Compatibility Validation

The current backend does not provide complete hardware-level validation for every possible PC configuration.

### Order Tracking

Order statuses are currently managed through administrative actions rather than real-time logistics integration.

---

# 🔮 Future Improvements

Planned backend improvements include:

## 🔄 Automated Data Synchronization

* Scheduled scraping
* Better retailer synchronization
* Stock monitoring
* Price-change detection

## 🧩 Advanced Compatibility Engine

Support for:

* CPU socket validation
* Motherboard compatibility
* RAM compatibility
* GPU dimensions
* Case clearance
* PSU connector validation
* BIOS compatibility

## 🤖 Advanced AI Recommendations

Future versions can consider:

* Specific games
* Target FPS
* Resolution
* AI model size
* VRAM requirements
* Rendering requirements
* Software-specific workloads

## 📊 Analytics

Future administrative APIs can provide:

* Sales statistics
* Popular products
* Retailer performance
* Order trends
* Revenue analytics

---

# 🔗 Related Projects

### Frontend

https://github.com/Sanzid-Ahmed/PC_Build

### Live Application

https://pc-build-ten.vercel.app/

---

# 👥 Development Team

Developed by students from the **Department of Computer Science & Engineering, United International University, Dhaka, Bangladesh**.

| Member             | Role      |
| ------------------ | --------- |
| **Sanzid Ahmed**   | Developer |
| **Ali Omar Nafiz** | Developer |
| **Tahsin Haque**   | Developer |
| **Ahmed Rayeed**   | Developer |

---

# 📄 License

This project does not currently specify an open-source license.

If the project is released under an official license in the future, this section should be updated accordingly.

---

<div align="center">

## ⚙️ ThriftBuild Backend

**Powering the ThriftBuild PC Building Platform**

Built with **Python + FastAPI + MySQL**

</div>
