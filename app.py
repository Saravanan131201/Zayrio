from flask import Flask, render_template, request, redirect,jsonify, session, url_for, flash
from flask_bcrypt import Bcrypt
from datetime import datetime
from datetime import timedelta
from db import users, products, cart, orders, wishlist, reviews, feedbacks
from auth import login_required
from statistics import mean
import uuid
import os

app = Flask(__name__)
app.secret_key = "secret-key"

bcrypt = Bcrypt(app)

reset_tokens = {}

folder_name = 'static/images'
os.makedirs(folder_name, exist_ok=True)



@app.route('/')
def index():
    all_feedbacks = list(feedbacks.find())
    return render_template("index.html", all_feedbacks =all_feedbacks)




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        password = request.form['password']
        confirm_password = request.form['c_pass']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        email = request.form['email']

        if bcrypt.check_password_hash(hashed_password, confirm_password):
            normal_user = {
            "user_id": str(uuid.uuid4()),
            "username": request.form['u_name'],
            "fullname": request.form['name'],
            "email": email,
            "phone" : request.form['phone'],
            "address" : request.form['address'],
            "gender" : request.form['gender'],
            "dob" : request.form['dob'],
            "age" : int(request.form['age']),
            "password": hashed_password,
            "created_at" : datetime.now(),
            "role": "admin" if email == "admin@textiles.com" or email == "admin1@textiles.com" else "user"
            }

            existing_username = users.find_one({"username" : normal_user['username']})

            if existing_username:
                flash("Username already exists")
                
            users.insert_one(normal_user)
            flash("Registered Sucessfully, It's Time to Log In", 'success')
            return redirect(url_for('login')) 
        
        else:
            flash("Password Doesn't match...Try again", 'danger')
            return render_template("register.html")
        

    
    return render_template("register.html")




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.find_one({"email": email})

        if user:
            check_password = bcrypt.check_password_hash(user['password'], password)

        if user and check_password:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["fullname"] = user["fullname"]
            session["gender"] = user["gender"]
            session["age"] = user["age"]
            session["email"] = user["email"]
            session["phone"] = user["phone"]
            session["dob"] = user["dob"]
            session["address"] = user["address"]
            session["logged_in_at"] = datetime.now()
            session["role"] = user["role"]

            flash("You've Successfully Loggged In", 'success')

            if session['role'] == "admin":
                return redirect(url_for('admin'))

            return redirect(url_for('user_profile'))
        else:
            flash("Invalid credentials !!!", 'error')

    return render_template("login.html")


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = users.find_one({'email': email})
        if user:
            token = str(uuid.uuid4())
            reset_tokens[token] = user['user_id']
            flash("Password reset link generated.", "info")
            return redirect(url_for('reset_password', token=token))
        else:
            flash("Email not found", "danger")
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = reset_tokens.get(token)
    if not user_id:
        flash("Invalid or expired token", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
        users.update_one({"user_id": user_id}, {"$set": {"password": hashed_pw}})
        reset_tokens.pop(token)
        flash("Password updated successfully", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')



@app.route('/logout')
def logout():
    session.clear()
    flash("You've Successfully Logged Out", 'success')
    return redirect(url_for('login'))



@app.context_processor
def inject_counts():
    if 'user_id' in session and session.get('role') == 'user':
        user_id = session['user_id']
        cart_count = cart.count_documents({'user_id': user_id})
        wishlist_count = wishlist.count_documents({'user_id': user_id})
    else:
        cart_count = 0
        wishlist_count = 0

    return dict(cart_count=cart_count, wishlist_count=wishlist_count)



# ============== user logic goes here ================

@app.route('/user_profile', methods=['GET', 'POST'])
@login_required(role="user")
def user_profile():
    user_id = session.get("user_id")  
    user_orders = list(orders.find({"user_id": user_id})) 
    total_orders = len(user_orders)

    delivered_statuses = [
    "Delivered",
    "Exchange Cancelled",
    "Return Cancelled",
    "Return In Progress",
    "Exchange In Progress"
    ]

    delivered = sum(1 for order in user_orders if order.get("status") in delivered_statuses)
    inprogress = sum(1 for order in user_orders if order.get("status") == "In Progress")
    returned = sum(1 for order in user_orders if order.get("status") == "Returned")
    exchanged = sum(1 for order in user_orders if order.get("status") == "Exchanged")
    cancelled = sum(1 for order in user_orders if order.get("status") == "Cancelled")
    delayed = sum(1 for order in user_orders if order.get("status") == "Delayed")
 
    return render_template("user/user_profile.html", 
                           user_order=user_orders, 
                           total_orders=total_orders,
                           delivered=delivered,
                           inprogress=inprogress,
                           returned = returned,
                           exchanged = exchanged,
                           cancelled = cancelled,
                           delayed = delayed
                           )



@app.route('/user_profile/edit_ profile', methods=['GET', 'POST'])
@login_required(role="user")
def edit_profile():
    user_id = session.get('user_id') 

    user = users.find_one({'user_id': user_id})

    if request.method == 'POST':
        updated_data = {
            'username': request.form['username'], 
            'fullname': request.form['fullname'],
            'email' : request.form['email'],
            'phone': request.form['phone'],
            'gender': request.form['gender'],
            'dob':request.form['dob'],
            'age': int(request.form['age']),
            'address': request.form['address']
        }

        users.update_one(
            {'user_id': user_id}, 
            {'$set': updated_data}
            )

        session.update(updated_data)

        flash('Profile updated successfully.')
        return redirect(url_for('user_profile'))

    return render_template('user/edit_profile.html', user=user)




@app.route('/products/<category>')
def view_products(category):
    selected_subcategory = request.args.get('subcategory')
    selected_brand = request.args.get('brand')
    selected_price = request.args.get('price')
    selected_discount = request.args.get('discount')

    source = request.args.get('source')

    page = int(request.args.get('page', 1))
    per_page = 12

    if source == "main":
        filtered = list(products.find({"product_type" : category}))

        if selected_subcategory and selected_subcategory != "All":
            filtered = [p for p in filtered if p.get("category") == selected_subcategory]

        if selected_brand and selected_brand != "All":
            filtered = [p for p in filtered if p.get("brand") == selected_brand]

        subcategories = sorted({
            prod.get("category")
            for prod in products.find({"product_type": category})
            if prod.get("category")
        })

        brands = sorted({
            prod.get("brand")
            for prod in products.find({"product_type": category})
            if prod.get("brand")
        })

    elif source == "hot_deals_main":
        filtered = list(products.find({"product_type": category}))

        if selected_subcategory and selected_subcategory != "All":
            filtered = [p for p in filtered if p.get("category") == selected_subcategory]

        if selected_brand and selected_brand != "All":  
            filtered = [p for p in filtered if p.get("brand") == selected_brand]

        subcategories = sorted({
            prod.get("category")
            for prod in products.find({"product_type": category})
            if prod.get("category")
        })

        brands = sorted({
            prod.get("brand")
            for prod in products.find({"product_type": category})
            if prod.get("brand")
        })

    
    elif source == "hot_deals":
        filtered = list(products.find({"category": category}))

        if selected_subcategory and selected_subcategory != "All":
            filtered = [p for p in filtered if p.get("subcategory") == selected_subcategory]

        if selected_brand and selected_brand != "All":
            filtered = [p for p in filtered if p.get("brand") == selected_brand]

        subcategories = sorted({
            prod.get("subcategory")
            for prod in products.find({"category": category})
            if prod.get("subcategory")
        })

        brands = sorted({
            prod.get("brand")
            for prod in products.find({"category": category})
            if prod.get("brand")
        })

    else:
        filtered = list(products.find({"category": category}))

        if selected_subcategory and selected_subcategory != "All":
            filtered = [p for p in filtered if p.get("subcategory") == selected_subcategory]

        if selected_brand and selected_brand != "All":
            filtered = [p for p in filtered if p.get("brand") == selected_brand]

        subcategories = sorted({
            prod.get("subcategory")
            for prod in products.find({"category": category})
            if prod.get("subcategory")
        })

        brands = sorted({
            prod.get("brand")
            for prod in products.find({"category": category})
            if prod.get("brand")
        })


    if selected_price and selected_price != "All":
        if selected_price == "<500":
            filtered = [p for p in filtered if p.get("discount_price", 0) < 500]
        elif selected_price == "500-1000":
            filtered = [p for p in filtered if 500 <= p.get("discount_price", 0) <= 1000]
        elif selected_price == ">1000":
            filtered = [p for p in filtered if p.get("discount_price", 0) >= 1000]
        elif selected_price == ">10000":
            filtered = [p for p in filtered if p.get("discount_price", 0) >= 10000]
        elif selected_price == ">50000":
            filtered = [p for p in filtered if p.get("discount_price", 0) >= 50000]

    if selected_discount and selected_discount != "All":
        if selected_discount == "10+":
            filtered = [p for p in filtered if p.get("discount", 0) >= 10]
        elif selected_discount == "25+":
            filtered = [p for p in filtered if p.get("discount", 0) >= 25]
        elif selected_discount == "50+":
            filtered = [p for p in filtered if p.get("discount", 0) >= 50]


    total_products = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_products = filtered[start:end]


    return render_template(
        "products.html",
        products=paginated_products,
        subcategories=subcategories,
        selected_subcategory=selected_subcategory,
        brands=brands,
        selected_brand=selected_brand,
        selected_price=selected_price,
        selected_discount=selected_discount,
        page=page,
        total_pages=(total_products + per_page - 1) // per_page,
        source=source,
        category=category
    )





@app.route('/search')
def search():
    query = request.args.get('q')
    page = int(request.args.get('page', 1))
    per_page = 12
    skip = (page - 1) * per_page

    
    total = products.count_documents({"name": {"$regex": query, "$options": "i"}})
    total_pages = (total + per_page - 1) // per_page

    results = list(products.find(
        {"name": {"$regex": query, "$options": "i"}}
    ).skip(skip).limit(per_page))

    return render_template("products.html", 
        products=results,
        search_mode=True,
        query=query,
        page=page,
        total_pages=total_pages
    )




@app.route('/product/<product_id>/review', methods=['POST'])
def submit_review(product_id):
    if 'username' not in session:
        flash("You must be logged in to post a review", "warning")
        return redirect(url_for('login'))

    review_text = request.form.get('review_text')
    rating = int(request.form.get('rating'))

    review = {
        "review_id" : str(uuid.uuid4()),
        "product_id": product_id,
        "username": session['username'],
        "fullname" : session['fullname'],
        "email" : session['email'],
        "phone" : session['phone'],
        "address" : session['address'],
        "text": review_text,
        "rating": rating
    }

    reviews.insert_one(review)
    flash("Review submitted successfully!", "success")
    return redirect(url_for('product_summary', product_id=product_id ))



@app.route('/feedback', methods=['GET', 'POST'])
@login_required(role='user')
def submit_feedback():

    order_exists = orders.count_documents(
        {"fullname": session['fullname'], 
         "status": { "$in": ["Delivered", "Returned", "Exchanged", "Return Cancelled", "Exchange Cancelled"] }
         }) >= 1

    if request.method == 'POST':

        if 'username' not in session:
            flash("You must be logged in to post a feedback", "warning")
            return redirect(url_for('login'))

        feedback_text = request.form.get('feedback_text')
        rating = int(request.form.get('rating'))

        feedback = {
            "feedback_id" : str(uuid.uuid4()),
            "username": session['username'],
            "fullname" : session['fullname'],
            "email" : session['email'],
            "phone" : session['phone'],
            "address" : session['address'],
            "text": feedback_text,
            "rating": rating
        }

        feedbacks.insert_one(feedback)
        flash("Feedback submitted successfully!", "success")

    return render_template('user/leave_feedbacks.html', order_exists = order_exists)





@app.route('/product/<product_id>')
def product_summary(product_id):
    product = products.find_one({"product_id": product_id})
    reviews_list = list(reviews.find({"product_id": product_id}))

    ratings = [review.get("rating", 0) for review in reviews_list if "rating" in review]
    average_rating = round(mean(ratings), 1) if ratings else None
    review_count = len(ratings)


    is_verified_buyer = False
    if session.get('username') and session.get('role') == 'user':
        is_verified_buyer = orders.count_documents({
            "user_id": session.get("user_id"),
            "product_id": product_id,
            "status": { "$in": ["Delivered", "Exchanged", "Return Cancelled", "Exchange Cancelled"] }
        }) >= 1



    verified_users = set(order["fullname"] for order in orders.find({
        "product_id": product_id,
         "status": { "$in": ["Delivered", "Returned", "Exchanged", "Return Cancelled", "Exchange Cancelled"] }
    }))

    return render_template("user/product_summary.html", 
                           product=product, 
                           reviews=reviews_list,
                           average_rating=average_rating,
                           review_count=review_count,
                           is_verified_buyer=is_verified_buyer,
                           verified_users=verified_users
                          )




@app.route('/add-to-cart/<product_id>', methods=['POST'])
@login_required(role="user")
def add_to_cart(product_id):
    product = products.find_one({"product_id": product_id})

    if product:
        quantity = int(request.form['quantity'])
        total_price = int(quantity * product['discount_price'])
        product_type = product.get("product_type")

        size = request.form.get("size") if product_type == "Clothing" else None

        cart_data = {
            "user_id": session["user_id"],
            "username": session['username'],
            "fullname" : session['fullname'],
            "product_id": product_id,
            "product_type" : product["product_type"],
            "name": product["name"],
            "price": product["price"],
            "discount_price": product["discount_price"],
            "image": product["image"],
            "quantity": quantity,
            "total_price": total_price
        }

        if product_type == "Clothing":
            cart_data["size"] = size

        cart.insert_one(cart_data)
        flash("Added to cart!")

    return redirect(url_for('view_cart'))




@app.route('/user_profile/cart')
@login_required(role="user")
def view_cart():
    user_cart = list(cart.find({"user_id": session["user_id"]}))
    return render_template("user/cart.html", cart_items=user_cart)


@app.route('/delete_from_cart/<product_id>', methods=['POST'])
def delete_from_cart(product_id):
    username = session['username']
    cart.delete_one({'username': username, 'product_id': product_id})
    flash("Item removed from cart.")
    return redirect(url_for('view_cart'))



@app.route('/add-to-wishlist/<product_id>', methods=['POST'])
@login_required(role="user")
def add_to_wishlist(product_id):
    product = products.find_one({"product_id": product_id})

    if product:
        quantity = int(request.form['quantity'])
        total_price = int(quantity * product['discount_price'])
        product_type = product.get("product_type")
        size = request.form.get("size") if product_type == "Clothing" else None

        wishlist_data = {
            "user_id": session["user_id"],
            "username": session['username'],
            "fullname" : session['fullname'],
            "product_id": product_id,
            "product_type" : product["product_type"],
            "name": product["name"],
            "price": product["price"],
            "discount_price": product["discount_price"],
            "image": product["image"],
            "quantity": quantity,
            "total_price": total_price
        }

        if product_type == "Clothing":
            wishlist_data["size"] = size

        wishlist.insert_one(wishlist_data)
        flash("Added to wishlist!")

    return redirect(url_for('view_wishlist'))



@app.route('/user_profile/view_wishlist')
@login_required(role="user")
def view_wishlist():
    user_wishlist = list(wishlist.find({"user_id" : session['user_id'] }))
    return render_template("user/wishlist.html", wishlist_items = user_wishlist)


@app.route('/delete_from_wishlist/<product_id>', methods=['POST'])
def delete_from_wishlist(product_id):
    username = session['username']
    wishlist.delete_one({'username': username, 'product_id': product_id})
    flash("Item removed from Wishlist.")
    return redirect(url_for('view_wishlist'))


@app.route('/user_profile/view_my_orders')
@login_required(role="user")
def view_user_orders():
    user_orders = list(orders.find({"user_id" : session['user_id'] }))
    return render_template("user/user_orders.html", my_orders = user_orders)


    
@app.route('/user_profile/view_my_orders/track_my_order', methods=['GET', 'POST'])
@login_required(role="user")
def track_my_order():
    order_id = request.form.get('order_id') or request.args.get('order_id')  

    user_order = list(orders.find({"user_id": session['user_id'], "order_id": order_id}))

    if not user_order:
        flash("Enter Your Order ID Correctly", "danger")
        return redirect(url_for('view_user_orders'))

    return render_template("user/track_orders.html", tracked_order=user_order, datetime = datetime)





@app.route('/cancel_order/<order_id>', methods=['POST'])
def cancel_order(order_id):
    user_id = session.get('user_id')  
    order = orders.find_one({"order_id": order_id, "user_id": user_id})

  
    if order and order['status'] not in ['Cancelled', 'Delivered']:
        reasons = request.form.getlist('reason[]')
        reason_text = ', '.join(reasons) if reasons else "No reason provided"
        
        orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "Cancelled", 
                          "cancel_reason": reason_text,
                          "cancelled_at" : datetime.now()
                          }}
            )
        
        flash("Order Cancelled Successfully")

    return redirect(url_for('track_my_order', order_id = order_id))



@app.route('/return_order/<order_id>', methods=['POST'])
@login_required(role="user")
def return_order(order_id):
    reasons = request.form.getlist("reason[]")
    reason_text = ', '.join(reasons) if reasons else "No reason provided"
    return_requested_at = datetime.now()

    orders.update_one(
        {"order_id": order_id, "user_id": session["user_id"]},
        {"$set": {
            "return_reason": reason_text,
            "return_requested_at": return_requested_at,
            "return_money_on" : return_requested_at + timedelta(days = 3),
            "status" : "Return Inprogress"
        }}
    )
    flash("Return request submitted successfully.")
    return redirect(url_for("track_my_order", order_id=order_id))



@app.route('/exchange_order/<order_id>', methods=['POST'])
@login_required(role="user")
def exchange_order(order_id):
    reason_list = request.form.getlist('reason')  
    combined_reason = ", ".join(reason_list)   
    exchange_requested_at = datetime.now()   

    new_size = request.form.get("new_size")
    update_fields = {
        "exchange_reason": combined_reason,
        "exchange_requested_at": exchange_requested_at,
        "exchange_delivered_on": exchange_requested_at + timedelta(days=3),
        "status" : "Exchange Inprogress"
    }

    if new_size:
        update_fields["exchange_new_size"] = new_size

    orders.update_one(
        {"order_id": order_id, "user_id": session["user_id"]},
        {"$set": update_fields}
    )
    flash("Exchange request submitted successfully.")
    return redirect(url_for("track_my_order", order_id=order_id))


@app.route('/cancel_return/<order_id>', methods=['POST'])
@login_required(role="user")
def cancel_return(order_id):
    order = orders.find_one({"order_id": order_id, "user_id": session["user_id"]})
    
    if order:
        request_time = order.get("return_requested_at")

        if request_time and (datetime.now() - request_time).days <= 3:
            orders.update_one(
                {"order_id": order_id},
                {
                    "$unset": {
                        "return_reason": "",
                        "return_requested_at": "",
                        "return_money_on": "",
                },
                    "$set": {
                        "return_cancelled_on": datetime.now(),
                        "status" : "Return Cancelled"
                        }
                }  
            )
            flash(f"Return request canceled.")

        else:
            flash("Cancellation period expired.", "danger")

    return redirect(url_for("track_my_order", order_id=order_id))



@app.route('/cancel_exchange/<order_id>', methods=['POST'])
@login_required(role="user")
def cancel_exchange(order_id):
    order = orders.find_one({"order_id": order_id, "user_id": session["user_id"]})
    
    if order:
        request_time = order.get("exchange_requested_at")

        if request_time and (datetime.now() - request_time).days <= 3:
                orders.update_one(
                    {"order_id": order_id},
                    {
                        "$unset": {
 
                            "exchange_reason": "",
                            "exchange_requested_at": "",
                            "exchange_delivered_on" : "",
                            "exchange_new_size": ""
                        },
                        "$set": {
                            "exchange_cancelled_on": datetime.now(),
                            "status": "Exchange Cancelled"
                        }
                    }
                )

                flash(f"Exchange request canceled.")

        else:
            flash("Cancellation period expired.", "danger")

    return redirect(url_for("track_my_order", order_id=order_id))





@app.route('/buy-now/<product_id>', methods=['POST'])
@login_required(role="user")
def buy_now(product_id):
    product = products.find_one({"product_id": product_id})

    if product:
        quantity = int(request.form['quantity'])
        discount_price = product['discount_price']
        total_price = int(quantity * discount_price)
        
        source = request.form['source']

        product_type = product.get("product_type")

        if discount_price <= 699:
            total_price += 80


        size = request.form.get('size') if product_type == "Clothing" else None

        session['checkout_item'] = {
            "product_id": product_id,
            "product_type": product_type,
            "name": product['name'],
            "price": product['price'],
            "discount_price": product['discount_price'],
            "quantity": quantity,
            "total_price": total_price,
            "source": source,
            "image": product['image'],
            "size": size
        }

        return redirect(url_for('checkout'))

    flash("Product not found.")
    return redirect(url_for('index'))



@app.route('/checkout')
@login_required(role="user")
def checkout():
    item = session.get('checkout_item')
    if not item:
        flash("No item to checkout.")
        return redirect(url_for('index'))
    return render_template('user/checkout.html', item=item)




@app.route('/place-order', methods=['POST'])
@login_required(role="user")
def place_order():
    username = session['username']
    user_find = users.find_one({"username": username})

    item = session.pop('checkout_item', None)

    if item and user_find:
        ordered_time = datetime.now()

        order_data = {
            "order_id": str(uuid.uuid4()), 
            "user_id": session["user_id"],
            "fullname": user_find['fullname'],
            "phone": user_find['phone'],
            "address": user_find['address'],
            "product_id": item["product_id"],
            "product_type" : item["product_type"],
            "name": item["name"],
            "price": item["price"],
            "discount_price": item["discount_price"],
            "quantity": item["quantity"],
            "total_price": item["total_price"],
            "ordered_at": ordered_time,
            "delivered_at": ordered_time + timedelta(days=3), 
            "image": item["image"],
            "status" : "In Progress",
        }

       
        if item.get("product_type") == "Clothing":
            order_data["size"] = item.get("size")

        orders.insert_one(order_data)

        source = item.get('source')

        if source == "cart_single":
            cart.delete_one({"user_id": session["user_id"], "product_id": item["product_id"]})
        elif source == "wishlist":
            wishlist.delete_one({"user_id": session["user_id"], "product_id": item["product_id"]})

        flash("Order placed successfully!")
        return render_template("user/thankyou.html")

    flash("Order failed.")
    return redirect(url_for('checkout'))



# @app.route('/sed')
# def show_session_data():
#     return jsonify(dict(session))



# =========== admin logic goes here ===================


@app.route('/admin', methods=['GET', 'POST'])
@login_required(role="admin")
def admin():
    admin_email = session.get('email')
    admin_fullname = session.get('fullname')

    admin_user = users.find_one({"email": admin_email, "role": "admin"})
    
    added_products = list(products.find({'added_by' : admin_fullname}))
    total_added_products = len(added_products)

    updated_orders = list(orders.find({'status_updated_by' : admin_fullname}))
    total_updated_orders = len(updated_orders)    
  


    return render_template(
        "admin/admin.html", 
        admin_user=admin_user, 
        total_added_products = total_added_products,
        total_updated_orders = total_updated_orders
        )



@app.route('/admin/show_all_users/', methods = ['GET'])
@login_required(role="admin")
def show_users():
    all_users = list(users.find({"role" : "user"}))

    return render_template('admin/show_users.html', all_users = all_users)




@app.route('/admin/show_all_orders', methods = ['GET'])
@login_required(role="admin")
def show_orders():
    all_orders = list(orders.find())

    return render_template('admin/show_orders.html', all_orders = all_orders)


@app.route('/admin/show_all_feedbacks', methods = ['GET'])
@login_required(role="admin")
def show_user_feedbacks():
    all_feedbacks = list(feedbacks.find())
    
    for feedback in all_feedbacks:
        fullname = feedback.get('fullname')  
        order_count = orders.count_documents({"fullname": fullname})
        feedback['order_count'] = order_count

    return render_template('admin/view_user_feedbacks.html', all_feedbacks = all_feedbacks)



@app.route('/admin/delete_feedback/<feedback_id>', methods=['POST'])
@login_required(role='admin') 
def delete_feedback(feedback_id):
    feedbacks.delete_one({'feedback_id' : feedback_id})
    flash("Feedback deleted successfully.", "success")
    return redirect(url_for('show_user_feedbacks'))




@app.route('/admin/show_all_reviews', methods = ['GET'])
@login_required(role="admin")
def show_user_reviews():
    all_reviews = list(reviews.find())

    for review in all_reviews:
        product = products.find_one({"product_id": review.get("product_id")})
        review["product_image"] = product.get("image") if product else None
        review["product_name"] = product.get("name") if product else "Unknown Product"

    return render_template('admin/view_user_reviews.html', all_reviews = all_reviews)


@app.route('/admin/delete_review/<review_id>', methods=['POST'])
@login_required(role='admin') 
def delete_review(review_id):
    reviews.delete_one({'review_id' : review_id})
    flash("Review deleted successfully.", "success")
    return redirect(url_for('show_user_reviews'))





@app.route('/admin/add_products/', methods = ['GET', 'POST'])
@login_required(role="admin")
def add_products():
    if request.method == 'POST':
        image = request.files['image']
        product_type = request.form['main_category']
        
        if image:
            filename = image.filename
            folder_path =f"{folder_name}/{product_type}"
            os.makedirs(folder_path, exist_ok=True)

            image_path = f"{folder_path}/{filename}"
            image.save(image_path)   

        price = float(request.form['price'])
        discount = float(request.form['discount'])
        discount_price = int(price - (price * discount / 100))
        

        new_product = {
            "product_id": str(uuid.uuid4()),
            "name": request.form['name'],
            "product_description" : request.form['prod_description'],
            "product_details" : request.form['prod_details'],
            "brand" : request.form['brand'],
            "product_type" : product_type,
            "category": request.form['category'],
            "subcategory": request.form['subcategory'],
            "price": price,
            "discount" : discount,
            "discount_price" : discount_price,
            "added_by" : session['fullname'],
            "image" : f"images/{product_type}/{filename}"
        }


        products.insert_one(new_product)
        flash("Product Added Successfully", 'success')

    return render_template('admin/add_products.html')




@app.route('/admin/manage_products/', methods = ['GET', 'POST'])
@login_required(role="admin")
def manage_products():
    product = list(products.find())

    return render_template('admin/manage_products.html', products = product)



@app.route('/edit_product/<product_id>', methods=['GET', 'POST'])
@login_required(role="admin")
def edit_product(product_id):
    product = products.find_one({"product_id": product_id})

    if not product:
        flash("Product not found", "danger")
        return redirect(url_for('manage_products'))

    if request.method == 'POST':
        image = request.files.get('image')
        product_type = request.form['product_type']

        # Update image if provided
        if image and image.filename != "":
            filename = image.filename
            folder_path = os.path.join("static/images", product_type)
            os.makedirs(folder_path, exist_ok=True)
            image_path = os.path.join(folder_path, filename)
            image.save(image_path)
            image_db_path = f"images/{product_type}/{filename}"
        else:
            image_db_path = product["image"]

        price = float(request.form['price'])
        discount = float(request.form['discount'])
        discount_price = int(price - (price * discount / 100))

        updated_data = {
            "name": request.form['name'],
            "product_description": request.form['prod_description'],
            "product_details": request.form['prod_details'],
            "brand": request.form['brand'],
            "product_type": product_type,
            "category": request.form['category'],
            "subcategory": request.form['subcategory'],
            "price": price,
            "discount": discount,
            "discount_price": discount_price,
            "image": image_db_path
        }

        products.update_one({"product_id": product_id}, {"$set": updated_data})
        flash("Product updated successfully", "success")
        return redirect(url_for('manage_products'))

    return render_template("admin/edit_product.html", product=product)



@app.route('/delete/<product_id>')
@login_required(role="admin")
def delete_product(product_id):
    products.delete_one({"product_id": product_id})

    flash("Product Deleted Successfully", 'success')
    return redirect(url_for('manage_products'))




@app.route('/update-order-status/<order_id>', methods=['POST'])
@login_required(role="admin")
def update_order_status(order_id):
    new_status = request.form.get("status")
    order = orders.find_one({"order_id": order_id})

    if order and new_status:
        update_data = {"status": new_status}

        if new_status == "Delivered":
            update_data["delivered_at"] = datetime.now()

        elif new_status == "Delayed":
            current_delivered_at = order.get("delivered_at")
            if current_delivered_at:
                updated_date = current_delivered_at + timedelta(days=3)
            else:
                updated_date = datetime.now() + timedelta(days=3)

            update_data["delivered_at"] = updated_date
        
        elif new_status == "Returned":
            update_data["return_money_on"] = datetime.now()
        
        elif new_status == "Exchanged": 
            update_data["exchange_delivered_on"] = datetime.now()

        
        update_data["status_updated_by"] = session.get("fullname")

        orders.update_one(
            {"order_id": order_id}, 
            {"$set": update_data})
        flash("Order status updated!")

    return redirect(url_for('show_orders'))


    
if __name__ == '__main__':
    app.run(debug = True)
