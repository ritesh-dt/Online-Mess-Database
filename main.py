import os
import bcrypt
from datetime import date, datetime, timedelta
import random
from string import ascii_lowercase, ascii_uppercase, digits

from flask import Flask
from flask import render_template, redirect, url_for, request
from flask import session, flash, send_from_directory
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "Hello"

IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "bmp"]
SERVER_URL = "http://127.0.0.1:5000/"
ADMIN_EMAIL = "admin@onlinemess.com"

# Database Section
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "res/images"
app.permanent_session_lifetime = timedelta(minutes=5)
db = SQLAlchemy(app)


class UsersDB(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	first_name = db.Column(db.String(20), nullable=False)
	last_name = db.Column(db.String(20), nullable=False)
	password = db.Column(db.String(128), unique=True)
	email = db.Column(db.String(80))
	account_type = db.Column(db.String(80))
	verified = db.Column(db.Boolean)
	restaurant = db.Column(db.Integer)
	subscriptions = db.Column(db.String(300))

class RestaurantsDB(db.Model):
	id = db.Column(db.Integer, primary_key=True, unique=True)
	name = db.Column(db.String(80))
	menu = db.Column(db.String(80))
	rating = db.Column(db.Integer)
	address = db.Column(db.String(80))
	phone = db.Column(db.String(20))
	opening_timing = db.Column(db.String(80))
	closing_timing = db.Column(db.String(80))
	tags = db.Column(db.String(80))
	owner = db.Column(db.Integer)
	images = db.relationship('ImagesDB', backref='parent_rest')
	monthly_items = db.Column(db.String(300))
	vegetarian = db.Column(db.Boolean)
	average_cost = db.Column(db.Float)
	orders = db.Column(db.String)
	main_menu_name = db.Column(db.String)
	main_menu_price = db.Column(db.Float)

class ImagesDB(db.Model):
	id = db.Column(db.Integer, primary_key=True, unique=True)
	image_name = db.Column(db.String(40))
	parent_id = db.Column(db.Integer, db.ForeignKey("restaurantsDB.id"))

class OrdersDB(db.Model):
	id = db.Column(db.Integer, primary_key=True, unique=True)
	bill_id = db.Column(db.Integer, nullable=False)
	item = db.Column(db.String, nullable=False)
	quantity = db.Column(db.Integer, nullable=False)
	price = db.Column(db.Float, nullable=False)

class BillsDB(db.Model):
	id = db.Column(db.Integer, primary_key=True, unique=True)
	creator = db.Column(db.Integer, nullable=False)
	subscriber = db.Column(db.Integer, nullable=False)
	total_price = db.Column(db.Float, nullable=False)
	timestamp = db.Column(db.String, nullable=False)
	active = db.Column(db.Boolean, nullable=False)
	coupon = db.Column(db.String, nullable=False)

db.create_all()
# Database End

# Email sending
SENDER_EMAIL = ""
SENDER_PASS = ""

app.config.update(
	MAIL_SERVER = 'smtp.gmail.com',
	MAIL_PORT = '465',
	MAIL_USE_SSL = True,
	MAIL_USERNAME = SENDER_EMAIL,
	MAIL_PASSWORD = SENDER_PASS
)
#mail = Mail(app)

def send_email(recipient, subject, body):
	with app.app_context():
		mail.send_message(subject,
							sender=SENDER_EMAIL,
							recipients = [recipient],
							body = body)

reset_keys = {}
verification_codes = {}

def check_details(*details):
	for detail in details:
		if not detail:
			return False
	return True

@app.route("/")
def index():
	return redirect(url_for("home"))
@app.route("/home")
def home():
	# db.drop_all()
	# db.session.commit()
	if "user" in session:
		loggedIn = [session["username"], session["account_type"], session["user"]]
	else:
		loggedIn = None
	return render_template("home.html", logged_in=loggedIn)

@app.route("/search", methods=["GET"])
def search():
	query_result = []
	if request.method == "GET":
		text_query = request.args.get("text_query_name")
		if text_query != None:
			#query_result = RestaurantsDB.query.filter(RestaurantsDB.name.like(f"%{text_query_name}%")).all()
			text_query_list = text_query.split()
			query_result = RestaurantsDB.query.filter(RestaurantsDB.name.contains(text_query), RestaurantsDB.rating.isnot(None)).all()
			for restaurant in RestaurantsDB.query.all():
				#print(restaurant.rating)
				if restaurant in query_result or restaurant.rating == None:
					continue
				for text_query_item in text_query_list:
					if restaurant in query_result:
						continue
					for sub_address in restaurant.address.split(", "):
						if text_query_item in sub_address.split():
							query_result.append(restaurant)
							break
				for text_query_item in text_query_list:
					if restaurant in query_result:
						continue
					for tag in restaurant.tags.split(", "):
						if text_query_item in tag:
							query_result.append(restaurant)
							break
		else:
			text_query = ""

		#query_result = RestaurantsDB.query.filter(RestaurantsDB.name.in_(text_query.split())).all()
	if "user" in session:
		loggedIn = [session["username"], session["account_type"], session["user"]]
	else:
		loggedIn = None
	return render_template("search.html", logged_in=loggedIn, query_result=query_result, text_query=text_query)

@app.route("/login/<next>/<id>", methods=["GET", 'POST'])
@app.route("/login/<next>", methods=["GET", 'POST'])
def login(next, id=None):
	if request.full_path.replace("/login", ""):
		next = request.full_path.replace("/login", "")
	else:
		next = "/home"
	if request.method == "POST":
		text_email = request.form["text_email"]
		text_password = request.form["text_password"]
		if not check_details(text_email, text_password):
			flash("Please fill all the details", "error")
			return redirect(next or url_for("home"))

		currentUser = UsersDB.query.filter_by(email=text_email).first()
		if currentUser:
			if not bcrypt.checkpw(text_password.encode(), currentUser.password):
				flash("Incorrect password or email!!", "error")
				return redirect(next or url_for("home")) 
		else:
			flash("No such user, consider signing up", "error")
			return redirect(next or url_for("home"))
			
		currentUser = UsersDB.query.filter_by(email=text_email).first()
		session["user"] = currentUser.email
		session["username"] = f"{currentUser.first_name} {currentUser.last_name}"
		session["account_type"] = currentUser.account_type
		session.permanent = True
		loggedIn = [session["username"], session["account_type"], session["user"]]

#	if "user" in session:
	return redirect(next or url_for("home"))
#	else:
#		return render_template("home.html", logged_in=loggedIn, pop_up=None)

@app.route("/signup/<next>/<id>", methods=["GET", 'POST'])
@app.route("/signup/<next>", methods=["GET", 'POST'])
def signup(next, id=None):
	if request.full_path.replace("/signup", ""):
		next = request.full_path.replace("/signup", "")
	else:
		next = "/home"
	
	if request.method == "POST":
		text_first_name = request.form["text_first_name"]
		text_last_name = request.form["text_last_name"]
		text_email = request.form["text_email"]
		text_password = request.form["text_password"]
		radio_account_type = request.form["radio_account_type"]

		if not check_details(text_first_name, text_last_name, text_email, text_password, radio_account_type):
			flash("Please fill all the details", "error")
			return redirect(next or url_for("home"))

		if not text_password == request.form["text_repeat_password"]:
			flash("Passwords do not match", "error")
			return redirect(next or url_for("home"))
		
		currentUser = UsersDB.query.filter_by(email=text_email).first()
		if currentUser:
			flash("Email already registered", "error")
			return redirect(next or url_for("home"))

		db.session.add(UsersDB(first_name=text_first_name, last_name=text_last_name, email=text_email, password=bcrypt.hashpw(text_password.encode(), bcrypt.gensalt()), account_type=radio_account_type, verified=0b0, restaurant=-1))
		db.session.commit()
		flash("Account registered successfully!!", "success")
		if radio_account_type == "Business":
			flash("Please fill in our restaurant details at 'Manage your business'")

		currentUser = UsersDB.query.filter_by(email=text_email).first()
		session["user"] = currentUser.email
		session["username"] = f"{currentUser.first_name} {currentUser.last_name}"
		session["account_type"] = currentUser.account_type
		session.permanent = True
		loggedIn = [session["username"], session["account_type"], session["user"]]

#	if "user" in session:
	return redirect(next or url_for("home"))
#	else:
#		return render_template("home.html", logged_in=[session["username"], session["account_type"]], pop_up=None)

@app.route("/forgot", methods=["POST", "GET"])
def forgot():
	global reset_keys
	allow_key = False
	text_email = ""
	label_text = "Reset password"
	if request.method == "POST":
		text_email = request.form["text_email"]
		if text_email:
			currentUser = UsersDB.query.filter_by(email=text_email).first()
			if currentUser:
				if "text_password_key" in request.form:
					text_password_key = request.form["text_password_key"]
					text_new_password = request.form["text_new_password"]
					if check_details(text_password_key, text_new_password):
						if bcrypt.checkpw(text_password_key.encode(), reset_keys[currentUser.email]):
							currentUser.password = bcrypt.hashpw(text_new_password.encode(), bcrypt.gensalt())
							db.session.commit()
							del reset_keys[currentUser.email]
							flash("Password changed", "success")
						else:
							flash("Invalid details", "error")
							allow_key = True
					else:
						flash("Please fill all the details")
						allow_key = True
					
				else:
					if currentUser.email in reset_keys:
						flash("Email has already been sent")
					else:
						reset_key = "".join([random.choice(ascii_lowercase + digits) for letter in range(8)])
						reset_keys[currentUser.email] = bcrypt.hashpw(reset_key.encode(), bcrypt.gensalt())
						#send_email(currentUser.email, "Password change requested", f"A password change request has been submitted for your account\n Your password reset key is {reset_key}\n If you did not request for the same, please ignore this email")
						flash("Email has been sent", "success")
					allow_key = True
			else:
				flash("Invalid email", "error")
	if "user" in session:
		text_email = session["user"]
		label_text = "Change your password"
		loggedIn = [session["username"], session["account_type"], session["user"]]
	else:
		loggedIn = None

	return render_template("forgot.html", logged_in=loggedIn, allow_key=allow_key, email=text_email, label_text=label_text)

@app.route("/logout")
def logout():
	if "user" in session:
		session.pop("user", None)
		session.pop("email", None)
		session.pop("username", None)
		session.pop("account_type", None)
		flash("Successfully logged out!!", "success")
	loggedIn = None
	return redirect(url_for("home", logged_in=loggedIn))

@app.route("/verify/<verification_code>")
def verify(verification_code):
	global verification_codes
	if verification_code in verification_codes:
		currentUser = UsersDB.query.filter_by(email=verification_codes[verification_code]).first()
		if currentUser:
			currentUser.verified = True
			db.session.commit()
			#print("Verified")
		del verification_codes[verification_code]
	return redirect(url_for("home"))

@app.route("/user", methods=["POST", "GET"])
def user():
	pass

@app.route("/upload/<filename>")
def send_image(filename):
	return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/restaurant/<restaurant_id>", methods=["POST", "GET"])
def restaurant(restaurant_id):
	if "user" in session:
		loggedIn = [session["username"], session["account_type"], session["user"]]
		currentUser = UsersDB.query.filter_by(email=session["user"]).first()
		if currentUser:
			subscribed_list = []
			currentBills = BillsDB.query.filter_by(subscriber=currentUser.id, creator=restaurant_id, active=0b1).all()
			if currentBills:
				updated_subscriptions = currentBills
				for bill in currentBills:
					if bill:
						end_date = datetime.strptime(bill.timestamp, '%Y-%m-%d %H:%M:%S.%f') +timedelta(days=1)

						restaurant = RestaurantsDB.query.filter_by(id=restaurant_id).first()
						if restaurant:
							if datetime.now() > end_date:
								updated_subscriptions.remove(bill)
								bill.active = 0b0
								bill.coupon = ""
								db.session.commit()
								flash(f"{restaurant.name} - Order expired on {end_date.strftime('%a, %d %b %Y')}", "error")
								continue
							bill_orders = OrdersDB.query.filter_by(bill_id=bill.id).all()
							items = []
							for order in bill_orders:
								#print("Order", order)
								items.append([order.item, order.quantity, order.price])

							subscribed_list.append([restaurant, items, bill.total_price, end_date.strftime("%a, %d %b %Y"), bill.coupon])

	else:
		loggedIn = None
		subscribed_list = None
	currentRest = RestaurantsDB.query.filter_by(id=restaurant_id).first()
	if currentRest:
		if request.method == "POST":
			#print(request.form)
			if "user" in session:
				currentUser = UsersDB.query.filter_by(email=session["user"]).first()
				coupon_code =  "".join([random.choice(ascii_uppercase + digits) for letter in range(6)])
				currentBill = BillsDB(creator=currentRest.id, subscriber=currentUser.id, timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"), total_price=float(request.form["text_total_price"]), active=0b1, coupon=coupon_code)
				db.session.add(currentBill)
				db.session.commit()

				#print(currentBill.id, request.form)
				menu = []
				for item in currentRest.menu.split("| "):
					menu.append(item.split("~"))
				for key in request.form.keys():
					if key != "text_total_price" and int(request.form[key]) > 0:
						item_index = int(key.split("_")[-1])
						if item_index == 11:
							item_name, item_price = currentRest.main_menu_name, currentRest.main_menu_price
						else:
							item_name, item_price = menu[item_index][:2] 
						item_count = int(request.form[key])
						#print(item_name, item_count)

						currentOrder = OrdersDB(bill_id=currentBill.id, item=item_name, quantity=item_count, price=item_count*float(item_price))
						db.session.add(currentOrder)
						db.session.commit()

				flash("Order successful!! You have to pay the price at the mess", "success")
				return redirect(url_for("restaurant", restaurant_id=restaurant_id))

			else:
				flash("Please login first!!", "error")
			return redirect(url_for("restaurant", restaurant_id=restaurant_id))
		menu = []
		for index, item in enumerate(currentRest.menu.split("| "), 0):
			menu.append(item.split("~")+[index])
		categorized_menu = {}
		for item in menu:
			if item[-2] not in categorized_menu:
				categorized_menu[item[-2]] = []
			categorized_menu[item[-2]].append(item)
		if currentRest.main_menu_name and currentRest.main_menu_price:
			categorized_menu["Our Speciality"] = [[currentRest.main_menu_name, currentRest.main_menu_price, "Our Speciality", 11]]
		#print(categorized_menu)
		return render_template("restaurant.html", restaurant=currentRest, logged_in=loggedIn, categorized_menu=categorized_menu, subscribed_list=subscribed_list)
	else:
		flash("Restaurant closed or no longer available", "error")
		return redirect(url_for("search"))

@app.route("/user/subscriptions", methods=["POST", "GET"])
def subscriptions():
	global verification_codes
	if not "user" in session:
		return redirect(url_for("logout"))
	else:
		loggedIn = [session["username"], session["account_type"], session["user"]]
	currentUser = UsersDB.query.filter_by(email=session["user"]).first()

	if not currentUser:
		flash("Please login again!!", "error")
		return redirect(url_for("logout"))
	if request.method == "POST":
		if "button_verify" in request.form:
			verification_code = "".join([random.choice(ascii_lowercase + digits) for letter in range(16)])
			verification_codes[verification_code] = currentUser.email
			#send_email(currentUser.email, "Email verification", f"Please verify this email for your account\n{SERVER_URL}/verify/{verification_code}")
			flash("Verification email has been sent", "success")
	subscribed_list = []
	currentBills = BillsDB.query.filter_by(subscriber=currentUser.id, active=0b1).all()
	if currentBills:
		updated_subscriptions = currentBills
		for bill in currentBills:
			if bill:
				restaurant_id = bill.creator
				end_date = datetime.strptime(bill.timestamp, '%Y-%m-%d %H:%M:%S.%f') +timedelta(days=1)

				restaurant = RestaurantsDB.query.filter_by(id=restaurant_id).first()
				if restaurant:
					if datetime.now() > end_date:
						updated_subscriptions.remove(bill)
						bill.active = 0b0
						bill.coupon = ""
						db.session.commit()
						flash(f"{restaurant.name} - Order expired on {end_date.strftime('%a, %d %b %Y')}", "error")
						continue
					bill_orders = OrdersDB.query.filter_by(bill_id=bill.id).all()
					items = []
					for order in bill_orders:
						#print("Order", order)
						items.append([order.item, order.quantity, order.price])

					subscribed_list.append([restaurant, items, bill.total_price, end_date.strftime("%a, %d %b %Y"), bill.coupon])
		#currentUser.subscriptions = ", ".join(updated_subscriptions)
		#db.session.commit()
	return render_template("subscriptions.html", logged_in=loggedIn, email=session["user"], subscribed_list=subscribed_list, verified=currentUser.verified)

@app.route("/user/restaurant", methods=["POST", "GET"])
def user_restaurant():
	if not "user" in session:
		return redirect(url_for("logout"))
	else:
		loggedIn = [session["username"], session["account_type"], session["user"]]
	currentUser = UsersDB.query.filter_by(email=session["user"]).first()

	if not currentUser:
		flash("Please login again!!", "error")
		return redirect(url_for("logout"))
	if currentUser.account_type == "Regular":
		flash("Permission denied (You don't have a business account)!!", "error")
		return redirect(url_for("subscriptions", logged_in=[session["username"], session["account_type"]]))
	currentRest = RestaurantsDB.query.filter_by(owner=currentUser.id).first()
	if not currentRest:
		currentRest = {key: "" for key in ["name", "address", "phone", "opening_timing", "closing_timing", "tags"]}
		list_menu = [("", "", "Other", 0) for i in range(11)]
		#list_menu[0] = ("", "", "Other", 1)
	else:
		list_menu = [tuple(item.split("~")) for item in currentRest.menu.split("| ")]
	if request.method == "POST":
		#print(request.form)
		if "file_image" in request.files:
			if "button_image_delete_" in str(request.form):
				for key in request.form:
					if "button_image_delete_" in key:
						image_id = int(key.split("_")[-1])
						imageObject = ImagesDB.query.filter_by(id=image_id).first()
						os.remove(os.path.join(app.config["UPLOAD_FOLDER"], f"{imageObject.image_name}"))
						db.session.delete(imageObject)
						db.session.commit()
			else:
				file_data = request.files["file_image"]
				if file_data.filename ==  "":
					flash("No file selected", "error")
				if file_data: # Image check
					next_filename = str(max([int(name.split(".")[0]) for name in os.listdir(app.config["UPLOAD_FOLDER"]) if name.split(".")[-1] in IMAGE_EXTENSIONS]+[0])+1)
					filename = secure_filename(next_filename + "." + file_data.filename.split(".")[-1])
					file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
					file_data.save(file_path)
					db.session.add(ImagesDB(image_name=filename, parent_rest=currentRest))
					db.session.commit()
		elif "text_name" in request.form:
			text_name = request.form["text_name"]
			if "checkbox_vegetarian" in request.form:
				checkbox_vegetarian = 0b1
			else:
				checkbox_vegetarian = 0b0
			text_address = request.form["text_address"]
			text_phone = request.form["text_phone"]
			text_timing_opening = request.form["text_timing_opening"]
			text_timing_closing = request.form["text_timing_closing"]
			text_tags = request.form["text_tags"]
			main_menu_name = request.form["main_menu_name"]
			main_menu_price = request.form["main_menu_price"]
			if checkbox_vegetarian == 0b1 and "vegan" not in text_tags:
				text_tags += ", vegan"
			text_menu_names = [request.form[f"text_menu_name_{i}"] for i in range(15) if f"text_menu_name_{i}" in request.form]
			text_menu_prices = [request.form[f"text_menu_price_{i}"] for i in range(15) if f"text_menu_price_{i}" in request.form]
			dropdown_categories = [request.form[f"dropdown_categories_{i}"] for i in range(15) if f"dropdown_categories_{i}" in request.form]
			#radio_search_display = int(request.form["radio_search_display"].split("_")[-1])

			#search_display = [0 for _ in range(15)]
			#search_display[radio_search_display] = 1
			#average_cost = sum(list(map(int, [item for item in text_menu_prices if item != ""])))/len([item for item in text_menu_names if item != ""])

			#text_menu_subscribe = [0 for _ in range(15)] 
			#for key in filter(lambda x: "checkbox_menu_subscribe_" in x, request.form.keys()):
			#	text_menu_subscribe[int(key.split("_")[-1])] = 1
			
			if not check_details(text_name, text_address, text_phone,  text_timing_opening, text_timing_closing, text_tags, text_menu_names, text_menu_prices, main_menu_name, main_menu_price):
				flash("Please fill all the restaurant details", "error")
			else:

				text_menu = "| ".join([f"{name}~{price}~{category}" for name, price, category in zip(text_menu_names, text_menu_prices, dropdown_categories)])

				if not RestaurantsDB.query.filter_by(owner=currentUser.id).first():
					flash("Register your restaurant successfully!!!", "success")
					flash("Your restaurant will be verified by our administration and then it will be open for customer orders!", "error")
					db.session.add(RestaurantsDB(name=text_name, address=text_address, phone=text_phone,  opening_timing=text_timing_opening, closing_timing=text_timing_closing, tags=text_tags, menu=text_menu, owner=currentUser.id,  vegetarian=checkbox_vegetarian, main_menu_name = main_menu_name, main_menu_price = main_menu_price, rating=None))
					currentRest = RestaurantsDB.query.filter_by(owner=currentUser.id).first()
				else:
					flash("Updated your restaurant details successfully!!!", "success")
					currentRest.name = text_name
					currentRest.address=text_address
					currentRest.phone=text_phone
					currentRest.opening_timing=text_timing_opening
					currentRest.closing_timing=text_timing_closing
					currentRest.tags=text_tags
					currentRest.menu=text_menu
					currentRest.owner=currentUser.id
					currentRest.vegetarian = checkbox_vegetarian
					currentRest.main_menu_name = main_menu_name
					currentRest.main_menu_price = main_menu_price
				db.session.commit()
			
				list_menu = [tuple(item.split("~")) for item in currentRest.menu.split("| ")]
		return redirect(url_for("user_restaurant"))
	#print("MENU", list_menu)
	return render_template("user_restaurant.html", logged_in=loggedIn, account_type=session["account_type"], restaurant=currentRest, menu=list_menu)

@app.route("/user/orders", methods=["POST", "GET"])
def orders():
	order_list = []
	if "user" in session:
		loggedIn = [session["username"], session["account_type"], session["user"]]
		currentUser = UsersDB.query.filter_by(email=session["user"]).first()
		if not currentUser:
			flash("Please login again!!", "error")
			return redirect(url_for("logout"))
		if currentUser.account_type == "Regular":
			flash("Permission denied (You don't have a business account)!!", "error")
			return redirect(url_for("subscriptions", logged_in=[session["username"], session["account_type"]]))
		currentRest = RestaurantsDB.query.filter_by(owner=currentUser.id).first()
		selected_list = []
		if currentRest:
			order_dict = {}
			currentBills = BillsDB.query.filter_by(creator=currentRest.id, active=0b1).all()
			if currentBills:
				if request.method == "POST":
					if "button_submit" in request.form:
						text_coupon_code = request.form.get("text_coupon_code")
						text_customer_email = request.form.get("text_customer_email")
						if not check_details(text_coupon_code, text_customer_email):
							flash("Please fill the required details", "error")
						else:
							subscriber_email = UsersDB.query.filter_by(email=text_customer_email).first()
							selectedBill = BillsDB.query.filter_by(coupon=text_coupon_code, subscriber=subscriber_email.id).first()
							if selectedBill:
								order_user = UsersDB.query.filter_by(id=selectedBill.subscriber).first()
								if order_user:
									bill_orders = OrdersDB.query.filter_by(bill_id=selectedBill.id).all()
									items = []
									for order in bill_orders:
										items.append([order.item, order.quantity, order.price])
									selected_list = [selectedBill.id,  f"{order_user.first_name} {order_user.last_name}", items, selectedBill.total_price, selectedBill.active]
							else:
								flash("Invalid coupon code or email", "error")
					elif "button_mark_used" in request.form:
						#print(request.form)
						text_order_info = int(request.form["text_order_info"])
						currentBill = BillsDB.query.filter_by(id=text_order_info, active=0b1).first()
						if currentBill:
							currentBill.active = 0b0
							db.session.commit()
				order_list = []
				currentBills = BillsDB.query.filter_by(creator=currentRest.id, active=0b1).all()
				for bill in currentBills:
					if bill:
						order_user = UsersDB.query.filter_by(id=bill.subscriber).first()
						if order_user:
							end_date = datetime.strptime(bill.timestamp, '%Y-%m-%d %H:%M:%S.%f') +timedelta(days=1)

							if datetime.now() > end_date:
								updated_subscriptions.remove(bill)
								bill.active = 0b0
								bill.coupon = ""
								db.session.commit()
								flash(f"{restaurant.name} - Order expired on {end_date.strftime('%a, %d %b %Y')}", "error")
								continue
							
							bill_orders = OrdersDB.query.filter_by(bill_id=bill.id).all()
							items = []
							for order in bill_orders:
								items.append([order.item, order.quantity, order.price])

					order_list.append([bill.id,  f"{order_user.first_name} {order_user.last_name}", items, bill.total_price, bill.active])
			else:
				flash("No active orders")
		else:
			flash("Please fill in your restaurant details in 'Manage your business'", "error")
	else:
		loggedIn = None
	return render_template("orders.html", logged_in=loggedIn, selected_list=selected_list, order_list=order_list)


@app.route("/learn", methods=["GET"])
def learn():
	if "user" in session:
		loggedIn = [session["username"], session["account_type"], session["user"]]
	else:
		loggedIn = None
	return render_template("learn.html", logged_in=loggedIn)

@app.route("/admin", methods=["POST", "GET"])
def admin():
	if "user" in session:
		loggedIn = [session["username"], session["account_type"], session["user"]]
		if not session["user"] == ADMIN_EMAIL:
			flash("Permission denied", "error")
			return redirect(url_for("home", logged_in=loggedIn))
		if request.method == "POST":
			for key in request.form:
				if "text_hygiene_rating_" in key:
					restaurant_id = int(key.split("_")[-1])
					text_rating = int(request.form[key])
					currentRest = RestaurantsDB.query.filter_by(id=restaurant_id).first()
					if currentRest:
						currentRest.rating = text_rating
						db.session.commit()
		pending_list = RestaurantsDB.query.filter_by(rating=None).all()
		approved_list = RestaurantsDB.query.filter(RestaurantsDB.rating.isnot(None)).all()
		if request.method == "POST":
			#print("REDIRECTING....")
			return redirect(url_for("admin"))
		return render_template("admin.html", logged_in=loggedIn, pending_list=pending_list, approved_list=approved_list)
	else:
		loggedIn = None
		flash("Please login first!", "error")
		return redirect(url_for("home", logged_in=loggedIn))

if __name__ == "__main__":
	app.run(debug=True)