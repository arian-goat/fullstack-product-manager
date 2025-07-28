from flask import Flask, jsonify, request
from flask_cors import CORS # برای حل مشکل CORS
import sqlite3 # برای SQLite (توسعه محلی)
import os
import psycopg2 # برای PostgreSQL (محیط دپلوی)
from urllib.parse import urlparse # برای تجزیه URL دیتابیس PostgreSQL

# --- تنظیمات برنامه ---
app = Flask(__name__)
# فعال کردن CORS برای تمام روت‌ها. در محیط واقعی، بهتر است دامنه فرانت‌اند را مشخص کنید.
CORS(app) 

# --- تنظیمات برای سازنده: آرین رحیمی ---
CREATOR_NAME = "آرین رحیمی"
PROJECT_TITLE = "سیستم مدیریت محصولات آنلاین آرین"

# تابع کمکی برای اتصال به پایگاه داده
def get_db_connection():
    # بررسی می‌کنیم که آیا متغیر محیطی DATABASE_URL (برای PostgreSQL در محیط‌های ابری) تنظیم شده است یا خیر.
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        # اگر DATABASE_URL وجود دارد، به PostgreSQL متصل می‌شویم.
        print("Connecting to PostgreSQL...")
        try:
            # تجزیه URL دیتابیس برای استخراج اطلاعات اتصال
            result = urlparse(database_url)
            username = result.username
            password = result.password
            database = result.path[1:] # حذف اسلش اول
            hostname = result.hostname
            port = result.port if result.port else 5432 # پورت پیش‌فرض PostgreSQL

            conn = psycopg2.connect(
                database=database,
                user=username,
                password=password,
                host=hostname,
                port=port,
                sslmode='require' # معمولا برای اتصال به PostgreSQL در محیط‌های ابری نیاز است
            )
            # برای psycopg2، fetchall() نتایج را به صورت تاپل برمی‌گرداند.
            # ما در API ها آن‌ها را به دیکشنری تبدیل می‌کنیم تا یکپارچه باشند.
            return conn
        except Exception as e:
            print(f"Error connecting to PostgreSQL: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")
    else:
        # اگر DATABASE_URL تنظیم نشده باشد، از SQLite برای توسعه محلی استفاده می‌کنیم.
        print("DATABASE_URL not found. Connecting to SQLite (for local development)...")
        sqlite_db_path = os.path.join(app.root_path, 'products.db')
        conn = sqlite3.connect(sqlite_db_path)
        # برای SQLite، این خط باعث می‌شود که نتایج کوئری‌ها به صورت دیکشنری (Row objects) برگردند.
        conn.row_factory = sqlite3.Row 
        return conn

# تابع برای ایجاد جدول محصولات در صورت عدم وجود (هم برای SQLite و هم PostgreSQL)
def init_db():
    conn = None # مقداردهی اولیه برای اطمینان از تعریف شدن
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if os.environ.get('DATABASE_URL'): # اگر PostgreSQL باشد
            # SERIAL PRIMARY KEY معادل AUTOINCREMENT در PostgreSQL است.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    price REAL NOT NULL
                )
            ''')
            print(f"[{PROJECT_TITLE}] پایگاه داده و جدول 'products' (PostgreSQL) راه‌اندازی شد (در صورت نیاز).")
        else: # اگر SQLite باشد (توسعه محلی)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    price REAL NOT NULL
                )
            ''')
            print(f"[{PROJECT_TITLE}] پایگاه داده و جدول 'products' (SQLite) راه‌اندازی شد (در صورت نیاز).")
            
        conn.commit()
    except Exception as e:
        print(f"Error during database initialization: {e}")
        # در اینجا می‌توانید خطا را به نحو مناسب‌تر مدیریت کنید (مثلاً log کنید).
    finally:
        if conn:
            conn.close()

# تابع کمکی برای تبدیل Row/Tuple به دیکشنری (برای یکپارچگی خروجی)
def row_to_dict(row):
    if isinstance(row, sqlite3.Row):
        return dict(row)
    elif isinstance(row, tuple):
        # برای psycopg2، اگر از RealDictCursor استفاده نشده باشد، باید دستی mapping انجام شود.
        # یا می‌توانیم نام ستون‌ها را در کوئری SELECT * FROM products بگیریم
        # اما برای سادگی، فعلا فرض می‌کنیم ترتیب ستون‌ها ثابت است.
        # در یک پروژه بزرگتر، ORM مثل SQLAlchemy این کار را بهتر انجام می‌دهد.
        # فرض می‌کنیم ترتیب: id, name, description, price
        # این بخش در یک سناریوی واقعی نیاز به مدیریت بهتری دارد اگر RealDictCursor استفاده نشود.
        # اما برای این پروژه آموزشی، می‌توانیم فرض کنیم که در Heroku از RealDictCursor استفاده خواهیم کرد
        # یا اینکه به سادگی به همان ترتیب در SQL کوئری می‌گیریم.
        # راه حل بهتر: RealDictCursor از psycopg2.extras را import و استفاده کنید.
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3]
        }
    return row # اگر هیچ‌کدام نبود، همان را برگردان

# --- API Endpoints ---

# 1. API برای افزودن یک محصول جدید (POST request)
@app.route('/products', methods=['POST'])
def add_product():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    new_product_data = request.get_json()
    name = new_product_data.get('name')
    description = new_product_data.get('description', '')
    price = new_product_data.get('price')

    if not name or not price:
        return jsonify({"error": "نام و قیمت محصول الزامی هستند."}), 400
    if not isinstance(name, str) or not isinstance(price, (int, float)):
        return jsonify({"error": "فرمت نام یا قیمت اشتباه است."}), 400
    if price <= 0:
        return jsonify({"error": "قیمت باید بیشتر از صفر باشد."}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # برای PostgreSQL، ID را به صورت RETURNING برمی‌گردانیم
        if os.environ.get('DATABASE_URL'):
            cursor.execute("INSERT INTO products (name, description, price) VALUES (%s, %s, %s) RETURNING id",
                           (name, description, price))
            product_id = cursor.fetchone()[0] # دریافت ID از نتیجه RETURNING
        else: # برای SQLite
            cursor.execute("INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
                           (name, description, price))
            product_id = cursor.lastrowid # ID محصول تازه اضافه شده

        conn.commit()
        return jsonify({
            "message": "محصول با موفقیت اضافه شد.",
            "product": {
                "id": product_id,
                "name": name,
                "description": description,
                "price": price
            }
        }), 201
    except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e:
        return jsonify({"error": "محصولی با این نام از قبل موجود است."}), 409
    except Exception as e:
        return jsonify({"error": f"خطا در افزودن محصول: {str(e)}"}), 500
    finally:
        conn.close()

# 2. API برای دریافت لیست تمام محصولات (GET request) یا جستجو
@app.route('/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # جستجو بر اساس نام یا توضیحات (case-insensitive)
        # برای PostgreSQL از ILIKE استفاده می‌شود
        if os.environ.get('DATABASE_URL'):
            cursor.execute("SELECT id, name, description, price FROM products WHERE name ILIKE %s OR description ILIKE %s",
                           (f"%{search_query}%", f"%{search_query}%"))
        else: # برای SQLite
            cursor.execute("SELECT id, name, description, price FROM products WHERE name LIKE ? OR description LIKE ?",
                           (f"%{search_query}%", f"%{search_query}%"))
        message = f"لیست محصولات با جستجوی '{search_query}'."
    else:
        cursor.execute("SELECT id, name, description, price FROM products")
        message = f"لیست تمام محصولات موجود."

    products = cursor.fetchall()
    conn.close()

    # تبدیل Row objects (برای SQLite) یا Tuple (برای psycopg2) به دیکشنری برای ارسال به صورت JSON
    products_list = [row_to_dict(product) for product in products]
    
    return jsonify({
        "message": message,
        "products": products_list
    }), 200

# 3. API برای دریافت جزئیات یک محصول خاص (GET request by ID)
@app.route('/products/<int:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # برای PostgreSQL از %s برای پارامتر استفاده می‌شود
    if os.environ.get('DATABASE_URL'):
        cursor.execute("SELECT id, name, description, price FROM products WHERE id = %s", (product_id,))
    else: # برای SQLite
        cursor.execute("SELECT id, name, description, price FROM products WHERE id = ?", (product_id,))
        
    product = cursor.fetchone()
    conn.close()

    if product:
        return jsonify(row_to_dict(product)), 200
    else:
        return jsonify({"error": "محصول یافت نشد."}), 404

# 4. API برای به‌روزرسانی یک محصول (PUT request)
@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    updated_data = request.get_json()
    name = updated_data.get('name')
    description = updated_data.get('description')
    price = updated_data.get('price')

    if not any([name is not None, description is not None, price is not None]):
        return jsonify({"error": "هیچ داده‌ای برای به‌روزرسانی ارائه نشده است."}), 400
    
    if name is not None and not isinstance(name, str):
        return jsonify({"error": "فرمت نام اشتباه است."}), 400
    if price is not None and not isinstance(price, (int, float)):
        return jsonify({"error": "فرمت قیمت اشتباه است."}), 400
    if price is not None and price <= 0:
        return jsonify({"error": "قیمت باید بیشتر از صفر باشد."}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        set_clauses = []
        params = []
        
        # نوع placeholder بر اساس نوع دیتابیس (PostgreSQL = %s, SQLite = ?)
        placeholder = '%s' if os.environ.get('DATABASE_URL') else '?'

        if name is not None:
            set_clauses.append(f"name = {placeholder}")
            params.append(name)
        if description is not None:
            set_clauses.append(f"description = {placeholder}")
            params.append(description)
        if price is not None:
            set_clauses.append(f"price = {placeholder}")
            params.append(price)
        
        if not set_clauses:
            return jsonify({"error": "هیچ داده معتبری برای به‌روزرسانی ارائه نشده است."}), 400

        params.append(product_id)
        
        # برای PostgreSQL، پارامترهای %s باید در یک تاپل جداگانه باشند، نه با ID محصول.
        # اینجاست که استفاده از ORM مثل SQLAlchemy خیلی ساده‌تر می‌شود.
        # اما برای دستی:
        if os.environ.get('DATABASE_URL'):
            query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = %s"
            cursor.execute(query, tuple(params))
        else: # برای SQLite
            query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, tuple(params)) # tuple(params) چون execute یک tuple می‌پذیرد.
            
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "محصول برای به‌روزرسانی یافت نشد."}), 404
        
        return jsonify({"message": "محصول با موفقیت به‌روزرسانی شد."}), 200
    except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e:
        return jsonify({"error": "محصولی با این نام از قبل موجود است."}), 409
    except Exception as e:
        return jsonify({"error": f"خطا در به‌روزرسانی محصول: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

# 5. API برای حذف یک محصول (DELETE request)
@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if os.environ.get('DATABASE_URL'):
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        else: # برای SQLite
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "محصول برای حذف یافت نشد."}), 404
        return jsonify({"message": "محصول با موفقیت حذف شد."}), 200
    except Exception as e:
        return jsonify({"error": f"خطا در حذف محصول: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

# --- اجرای برنامه Flask ---
if __name__ == '__main__':
    # این تابع را فقط یکبار در شروع اجرا می کنیم تا مطمئن شویم جداول ساخته شده‌اند.
    # در محیط دپلوی، این ممکن است توسط Heroku run command یا migration scripts انجام شود.
    init_db() 
    print(f"[{PROJECT_TITLE}] توسط {CREATOR_NAME} در حال اجراست...")
    print("سرور Flask در حال شروع به کار است.")
    print("\nAPI Endpoints:")
    print("  POST /products             : افزودن محصول جدید")
    print("  GET  /products             : دریافت لیست تمام محصولات (با پارامتر 'search' برای جستجو)")
    print("  GET  /products/<id>        : دریافت جزئیات یک محصول")
    print("  PUT  /products/<id>        : به‌روزرسانی محصول")
    print("  DELETE /products/<id>      : حذف محصول")
    print(f"\nبرای تست APIها می‌توانید از ابزارهایی مانند Postman، Insomnia یا VS Code Rest Client استفاده کنید.")
    print("سرور در این آدرس قابل دسترسی است: http://127.0.0.1:5000/")
    # اجرای Flask روی پورت محیطی یا 5000 برای توسعه
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))