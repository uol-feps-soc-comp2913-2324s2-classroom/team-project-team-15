import io
from operator import or_
from venv import logger
from flask import make_response, render_template, redirect, url_for, flash, request,session,jsonify, current_app
import gpxpy
from app import app, db
from app.models import SubscriptionPlan, User,Payment, FriendRequest, JourneyRecord
from app.forms import RegistrationForm
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from collections import defaultdict
import stripe
from datetime import date, datetime, timedelta
from functools import wraps
import csv
stripe.api_key = 'sk_test_51OubkTGiwWWmEjuUTmrjuRowLjdmFXb365kmtoD0YRLYf7rYKIVhFBIEwn3ozE4O1TMSIqcHa9WIk07RcbIqfErC00DyV65frs'



def create_stripe_customer(user):
    """
    Creates a new customer in the Stripe system using the user's details.
    
    Parameters:
        user (User object): The user object containing the user's information.
    
    Returns:
        str: The Stripe customer ID if the customer was successfully created.
        None: If the creation failed due to an exception.
    
    This function attempts to register a user as a customer in Stripe based on their
    email and name. It is useful for linking Stripe's payment functionalities with the user's account.
    """
    try:
        # Create a Stripe customer object
        customer = stripe.Customer.create(
            email=user.email,  # User's email address
            name=f"{user.firstname} {user.surname}",  # User's full name
            # Additional fields can be included if required
        )
        return customer.id  # Return the Stripe customer ID on success
    except Exception as e:
        print(f"Failed to create Stripe customer: {e}")
        return None  # Return None if there was an error during customer creation

    
def membership_required(f):
    """
    Decorator to restrict access to routes based on the user's membership status.
    
    This decorator ensures that a user has an active subscription before allowing access
    to specific routes. If the user's subscription has expired or does not exist, it
    redirects them to a subscription choice page.

    Parameters:
        f (function): The Flask view function to decorate.

    Returns:
        function: The decorated view function which includes the subscription check.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = current_user  # Access the current user from Flask-Login
        today = datetime.today().date()  # Get today's date for comparison
        # Check if user has a valid and non-expired subscription plan
        if not user.subscription_plan or user.subscription_plan.expiration_date < today:
            # Notify user and redirect if the subscription is expired or doesn't exist
            flash('Your membership is expired or does not exist. Please renew your membership.', 'warning')
            return redirect(url_for('choose_subscription'))
        return f(*args, **kwargs)  # Call the original function if the check passes
    return decorated_function



@app.route('/', methods=['GET'])
def index():
    """
    Serve the home page.
    This endpoint handles only GET requests.
    Returns:
        Rendered 'home.html' template for the site's home page.
    """
    return render_template('home.html')
        

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    - GET: Serve the registration form.
    - POST: Process the submitted registration form, create a new user, and register them.
    
    Returns:
        On GET: Rendered 'register.html' with the registration form.
        On POST: Redirects to the login page upon successful registration or reloads the form with error messages.
    """
    form = RegistrationForm(request.form) # Create form instance from submitted data
    if request.method == 'POST':
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        user = User(
            username=form.username.data,
            firstname=form.firstName.data,
            surname=form.surName.data,
            dob=form.dob.data,
            email=form.email.data,
            phone_number=form.phoneNumber.data,
            password_hash=hashed_password,
        )
        # Set default values
        user.journeys = [] # Initialize user's journeys list
        user.friends = [] # Initialize user's friends list
        user.subscription_plan_id = None # Initialize subscription plan ID
        stripe_customer_id = create_stripe_customer(user) # Attempt to create a Stripe customer
        if stripe_customer_id:
            user.stripe_customer_id = stripe_customer_id
            try:
                db.session.add(user) # Add new user to the database session
                db.session.commit()   # Commit changes to the database
                flash('Congratulations, you are now a registered user!')
                return redirect(url_for('login')) # Redirect to login upon success
            except Exception as e:
                print(e) # Print the error to the console
                db.session.rollback()  # Rollback the session on error
                flash('Registration failed due to an internal error.') # Show error message
        else:
            flash('Failed to create a Stripe customer account. Please try again.')        
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    - GET: Serve the login form.
    - POST: Authenticate the user and initiate a session.
    
    Returns:
        On GET: Rendered 'login.html' with the login form.
        On POST: Redirects based on user status or authentication outcome.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()  # Query the user from the database
        if user and check_password_hash(user.password_hash, password):  # Validate password
            if is_admin:
                return redirect(url_for('admin'))  # Special redirect for admin users
            login_user(user) 
            if not user.subscription_plan_id:
                return redirect(url_for('choose_subscription'))  # Redirect to subscription choice if not set
            return redirect(url_for('display_journeys'))  # Redirect to main content page
        else:
            flash('Invalid username or password')  # Show error if login fails
    return render_template('login.html')  # Render login form


@app.route('/logout')
@login_required
def logout():
    """
    Handle user logout.
    Logs out the user, clears the session, and redirects to the home page.

    Returns:
        Redirect to the home page.
    """
    logout_user()  # Log out the user using Flask-Login
    session.clear()  # Clear the session data
    return redirect(url_for('index'))  # Redirect to the home page 


def is_admin():
    """
    Check if the current logged-in user is an administrator.
    
    Returns:
        Boolean: True if the current user is authenticated as 'admin', False otherwise.
    """
    return (current_user.is_authenticated and current_user.username == 'admin'
            and current_user.password == 'adminPass')


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    """
    Admin dashboard view to manage users and subscriptions.
    Requires admin privileges to access and manage subscription data.
    
    Returns:
        Rendered 'admin.html' with various subscription and user data:
        - Total and weekly revenue calculations.
        - Subscription counts by plan.
        - User data and payment card expiry dates.
    """
    if is_admin():
        # Query users with active subscriptions
        active_subscriptions = User.query.filter(User.subscription_start_date.isnot(None)).all()
        Users = User.query.all()
        
        # Query all users and their payment card expiry dates if available
        users_with_expiry_dates = db.session.query(User, Payment.card_expiry_date).\
        outerjoin(Payment).all()

        # Initialize weekly revenue dictionary
        weekly_revenue = {}
        current_date = datetime.now().date()
        end_date = current_date + timedelta(days=365)

        # Populate initial weekly revenue data
        while current_date <= end_date:
            week_start = current_date - timedelta(days=current_date.weekday())
            weekly_revenue[week_start.strftime('%Y-%m-%d')] = 0
            current_date += timedelta(weeks=1)

        # Calculate weekly revenue from active subscriptions
        for user in active_subscriptions:
            subscription_plan = SubscriptionPlan.query.get(user.subscription_plan_id)
            if subscription_plan:
                start_date = user.subscription_start_date
                duration = subscription_plan.plan_name.lower()
                price = subscription_plan.price

                current_date = start_date
                while current_date <= end_date:
                    week_start = current_date - timedelta(days=current_date.weekday())
                    week_end = week_start + timedelta(days=6)
                    if current_date >= start_date and current_date <= week_end:
                        weekly_revenue[week_start.strftime('%Y-%m-%d')] += price
                    if duration == 'weekly':
                        current_date += timedelta(weeks=1)
                    elif duration == 'monthly':
                        current_date += timedelta(days=30)
                    elif duration == 'annually':
                        current_date += timedelta(days=365)
        
        # Sum and round total revenue
        total = round(sum(weekly_revenue.values()), 2)

        # Count subscriptions by plan
        subscription_counts = defaultdict(int)
        for user in User.query.filter(User.subscription_plan_id.isnot(None)).all():
            subscription_counts[user.subscription_plan.plan_name] += 1
        
        # Sort the revenue data by date
        sorted_weekly_revenue = sorted(weekly_revenue.items())

        # Render the admin dashboard
        return render_template('admin.html', revenue_data=sorted_weekly_revenue, 
                               subscription_counts=subscription_counts, Users=Users, 
                               users_with_expiry_dates=users_with_expiry_dates, total=total)



def get_stripe_plans():
    """
    Fetch active Stripe pricing plans and format them for display.
    Returns:
        A list of dictionaries, each representing a Stripe plan with details such as id, name, amount, currency, and interval.
    """
    try:
        prices = stripe.Price.list(active=True, expand=["data.product"])  # Retrieve active Stripe prices and expand product details
        plans = []
        for price in prices.data:
            plans.append({
                'id': price.id,  # Stripe price ID
                'name': price.product.name,  # Product name associated with the price
                'amount': price.unit_amount / 100,  
                'currency': price.currency, 
                'interval': price.recurring.interval 
            })
        return plans
    except Exception as e:
        print(f"Error fetching Stripe plans: {e}")  # Log the exception
        return []  # Return an empty list on failure


@app.route('/choose_subscription', methods=['GET','POST'])
@login_required
def choose_subscription():
    """
    Route to allow users to choose a subscription plan.
    Fetches available Stripe plans and current subscription details of the user.
    Returns:
        Rendered template for choosing subscriptions with data about available plans and current subscription.
    """
    plans = get_stripe_plans()# Fetch the current user's subscription details
    current_subscription = None
    if current_user.subscription_plan_id:
        subscription_plan = SubscriptionPlan.query.get(current_user.subscription_plan_id)
        if subscription_plan:
            current_subscription = {
                'plan_id': subscription_plan.id,
                'plan_name': subscription_plan.plan_name,
                'start_date': current_user.subscription_start_date,
                'expiration_date': subscription_plan.expiration_date, 
                'price_id':subscription_plan.stripe_price_id,
                'days_left': (subscription_plan.expiration_date - date.today()).days if subscription_plan.expiration_date else None
            }

    user = User.query.get(current_user.id)        
    subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status='active', limit=1)
    subscription_details = None
    if subscriptions.data:
        subscription = subscriptions.data[0]
        subscription_details = {
            'is_auto_renewal_on': not subscription.cancel_at_period_end,
        }         

    return render_template('choose_subscription.html', plans=plans, current_subscription=current_subscription,subscription_details=subscription_details)
       

@app.route('/create_checkout_session', methods=['GET', 'POST'])
@login_required
def create_checkout_session():
    """
    Route to initiate a Stripe checkout session for handling subscriptions.
    This function creates a checkout session with Stripe and redirects the user to complete the payment.

    Returns:
        Redirect to Stripe's checkout URL on successful creation of the session.
        On failure, redirects back to the subscription choice page with an error message.
    """
    user = current_user  # Get the current logged-in user
    
    # Ensure the user has a Stripe customer ID; create one if not present
    if not user.stripe_customer_id:
        create_stripe_customer(user)

    # Retrieve the Stripe price ID from the submitted form
    stripe_price_id = request.form.get('stripe_price_id')

    try:
        # Create a new Stripe checkout session with the specified configurations
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,  # Specify which Stripe customer this checkout is for
            payment_method_types=['card'],  # Define accepted payment methods, here just 'card'
            line_items=[{  # Define items included in this checkout session
                'price': stripe_price_id,  # Price ID from Stripe
                'quantity': 1,  # Number of subscriptions to buy
            }],
            mode="subscription",  # Specify the mode as subscription for recurring payments
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',  # URL to redirect to on payment success
            cancel_url=url_for('payment_cancel', _external=True),  # URL to redirect to if the payment is cancelled
            client_reference_id=str(user.id),  # Pass the user ID for reference in callbacks
            metadata={'stripe_price_id': stripe_price_id},  # Additional metadata to store with the session
        )
        # Redirect the user to Stripe's hosted checkout page
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        # Handle exceptions by flashing a failure message and redirecting to the subscription choice page
        flash(f"Failed to create a checkout session: {e}", 'error')
        return redirect(url_for('choose_subscription'))


@app.route('/payment_success', methods=['GET'], endpoint='payment_success')
@login_required
def payment_success():
    """
    Handles the redirection after a successful payment via Stripe. It retrieves the session details from Stripe,
    processes the subscription data, updates user records, and handles various edge cases like missing data.

    Returns:
        Redirect to 'display_journeys' on successful update, or redirect to the index page with an error message if an issue arises.
    """
    # Retrieve the session ID from query parameters
    session_id = request.args.get('session_id')
    if not session_id:
        flash('No payment session found.', 'error')  # Notify if no session is found
        return redirect(url_for('index'))  # Redirect to home if session ID is missing

    try:
        # Retrieve the Stripe session to obtain subscription and payment details
        session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = session.get('subscription')
        if not subscription_id:
            flash("Subscription ID not found.", 'error')  # Check if the subscription ID was successfully retrieved
            return redirect(url_for('index'))

        # Retrieve the subscription and related details from Stripe
        subscription = stripe.Subscription.retrieve(subscription_id)
        stripe_customer_id = subscription.customer
        stripe_price_id = session.metadata.get('stripe_price_id')
        price = stripe.Price.retrieve(stripe_price_id)
        product = stripe.Product.retrieve(price.product)

        # Calculate the subscription period
        start_date = datetime.utcfromtimestamp(subscription.current_period_start)
        end_date = datetime.utcfromtimestamp(subscription.current_period_end)
        duration_days = (end_date - start_date).days

        # Query or create a subscription plan in the local database
        subscription_plan = SubscriptionPlan.query.filter_by(stripe_customer_id=stripe_customer_id, stripe_price_id=stripe_price_id).first()
        if not subscription_plan:
            subscription_plan = SubscriptionPlan(stripe_customer_id=stripe_customer_id,stripe_price_id=stripe_price_id)
            db.session.add(subscription_plan)

        # Update the local subscription plan details
        subscription_plan.plan_name = product.name
        subscription_plan.price = price.unit_amount / 100  # Convert cents to dollars
        subscription_plan.duration = str(duration_days) 
        subscription_plan.expiration_date = datetime.utcfromtimestamp(subscription.current_period_end)
        
        # Link the subscription to the user
        user = User.query.get(int(session.get('client_reference_id')))
        if user:
            user.subscription_start_date = start_date  # Update user's subscription start date

        # Retrieve and update payment method details
        payment_methods = stripe.PaymentMethod.list(customer=user.stripe_customer_id, type="card")
        if payment_methods and payment_methods.data:
            card_details = payment_methods.data[0].card
            expiry_date = f"{card_details.exp_month}/{card_details.exp_year}"  # Format expiry date

        # Record the payment details in the database
        payment = Payment(
            user_id=user.id,
            amount=price.unit_amount / 100,  # Convert cents to dollars
            payment_date=datetime.utcnow(),
            payment_status=subscription.status,
            stripe_session_id=session_id,
            payment_method_type='card',
            card_expiry_date=expiry_date
        )
        db.session.add(payment)
        db.session.commit()  # Commit the database changes

        # Ensure the user's subscription plan ID is updated
        user = User.query.get(int(session.get('client_reference_id')))
        if user:
            user.subscription_plan_id = subscription_plan.id
        db.session.commit()    

        flash('Your payment was successful! Thank you for subscribing.', 'success')  # Notify user of success
    except Exception as e:
        db.session.rollback()  # Rollback the transaction in case of an error
        flash(f'There was an error confirming your payment: {e}', 'error')  # Error notification

    return redirect(url_for('display_journeys'))  # Redirect to the main journey display page


@app.route('/payment_cancel',methods=['GET'])
@login_required
def payment_cancel():
    """
    A simple route that handles the cancellation of a payment process.
    It informs the user that their payment attempt was canceled.
    
    Returns:
        Redirection to the index page with a warning message.
    """
    flash('Payment was canceled.', 'warning')  # Notify user about the cancellation
    return redirect(url_for('index'))  # Redirect to the home page


def is_payment_card_expired(user):
    """
    Checks if the user's payment card is expired.

    Parameters:
        user (User): The user object to check for expired card.

    Returns:
        bool: True if the card is expired, False otherwise.
    """
    if user.payments:
        # Get the most recent payment
        latest_payment = max(user.payments, key=lambda x: x.payment_date, default=None)
        if latest_payment and latest_payment.card_expiry_date:
            # Convert the stored expiry date string to a date object
            expiry_date = datetime.strptime(latest_payment.card_expiry_date, "%m/%Y")
            return expiry_date <= datetime.utcnow()  # Check if the card is expired
    return False


@app.route('/enable_auto_renewal', methods=['POST'])
@login_required
@membership_required
def enable_auto_renewal():
    """
    Enables auto-renewal for a user's subscription by updating the Stripe subscription details.

    Returns:
        Redirection to the index page with a success or error message.
    """
    user = User.query.get(current_user.id)
    if not user or not user.stripe_customer_id:
        flash('You do not have an active subscription.', 'error')
        return redirect(url_for('display_journeys'))

    try:
        # Retrieve the user's active subscriptions from Stripe
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
        subscription_id = None
        for subscription in subscriptions.auto_paging_iter():
            # Find the subscription that matches the user's current plan
            if subscription['items']['data'][0]['price']['id'] == user.subscription_plan.stripe_price_id:
                subscription_id = subscription['id']
                break
        
        if not subscription_id:
            flash('No active subscription found for auto-renewal.', 'error')
            return redirect(url_for('index'))
        
        # Enable auto-renewal
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=False)
        db.session.commit()  # Commit any changes to the database
        flash('Your subscription will be automatically renewed at the end of the current billing period.', 'success')
    except Exception as e:
        flash(f'An error occurred while enabling auto-renewal for your subscription: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/change_subscription/<string:new_plan_stripe_id>', methods=['POST'])
@login_required
def change_subscription(new_plan_stripe_id):
    """
    Changes the user's subscription plan to a new one based on the specified Stripe price ID.

    Parameters:
        new_plan_stripe_id (str): The Stripe price ID of the new subscription plan.

    Returns:
        Redirection to the subscription choice page with relevant messages.
    """
    user = User.query.get(current_user.id)
    if not user:
        flash('No user found.', 'error')
        return redirect(url_for('choose_subscription'))
    if is_payment_card_expired(user):
        flash('Your payment card has expired. Please update your payment method.', 'error')
        return redirect(url_for('update_card_details'))

    plans = get_stripe_plans()  # Fetch available plans from Stripe
    stripe_plan = next((plan for plan in plans if plan['id'] == new_plan_stripe_id), None)
    if not stripe_plan:
        flash('Plan not found.', 'error')
        return redirect(url_for('choose_subscription'))

    subscription_plan = SubscriptionPlan.query.filter_by(stripe_price_id=new_plan_stripe_id).first()
    if not subscription_plan:
        # Create new subscription plan if it doesn't exist
        subscription_plan = SubscriptionPlan(
            stripe_price_id=new_plan_stripe_id,
            plan_name=stripe_plan['name'],
            price=stripe_plan['amount'],
            duration=stripe_plan['interval'],
        )
        db.session.add(subscription_plan)
        db.session.flush()  # Flush to assign an ID if needed

    if user.subscription_plan and user.subscription_plan.expiration_date and user.subscription_plan.expiration_date > date.today():
        # Plan changes at the end of the current period
        user.subscription_plan.next_plan_id = subscription_plan.id
        user.subscription_plan.cancel_at_period_end = True
        flash('Your subscription will be updated at the end of your current period.', 'success')
    else:
        # Update immediately if no active or expired plan
        user.subscription_plan = subscription_plan
        user.subscription_start_date = date.today()
        flash('Your subscription has been updated.', 'success')
    
    db.session.commit()
    return redirect(url_for('choose_subscription'))


@app.route('/update_card_details', methods=['GET'])
@login_required
def update_card_details():
    """
    Route to initiate a Stripe Checkout session to update the user's payment card details.
    This is used when a user needs to update their card information.

    Returns:
        Redirect to the Stripe checkout URL on success, or back to the subscription choice page with an error message on failure.
    """
    user = User.query.get(current_user.id)  # Retrieve the current user's details
    try:
        # Create a Stripe Checkout session specifically configured for updating payment details
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],  # Accept only card payments
            customer=user.stripe_customer_id,  # Specify the Stripe customer ID
            mode='setup',  # Use 'setup' mode for updating payment details
            success_url=url_for('payment_method_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('handle_cancel', _external=True),
        )
        return redirect(session.url, code=303)  # Redirect to Stripe's setup session
    except Exception as e:
        flash(f"Failed to initiate payment method update: {e}", 'error')  # Show error message
        return redirect(url_for('choose_subscription'))  # Redirect to the subscription choice page


@app.route('/payment_method_success')
@login_required
def payment_method_success():
    """
    Handles the success callback after updating the payment method via Stripe.
    Updates the user's payment details in the local database.

    Returns:
        Redirect to the user profile page on success, or back to the subscription choice page with an error message on failure.
    """
    session_id = request.args.get('session_id')  # Get session ID from query parameters
    if not session_id:
        flash('No payment session found.', 'error')  # Notify if no session ID is found
        return redirect(url_for('choose_subscription'))  # Redirect to subscription choice

    try:
        # Retrieve the checkout session to access new payment method details
        session = stripe.checkout.Session.retrieve(session_id)
        new_payment_method = stripe.PaymentMethod.retrieve(session.payment_method)  # Retrieve the new payment method

        # Validate that the retrieved payment method matches the expected details
        if not new_payment_method or new_payment_method.customer != session.customer:
            flash('Mismatch in payment method details.', 'error')
            return redirect(url_for('choose_subscription'))

        # Detach all old payment methods to ensure only the new one is active
        old_payment_methods = stripe.PaymentMethod.list(customer=session.customer, type="card")
        for pm in old_payment_methods.data:
            if pm.id != new_payment_method.id:
                stripe.PaymentMethod.detach(pm.id)

        # Update the local database with the new card's expiry date
        update_local_payment_method(current_user.id, new_payment_method.card.exp_month, new_payment_method.card.exp_year)

        flash('Payment method updated successfully!', 'success')  # Notify user of success
    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error: {e.user_message}")
        flash(f"Stripe API error: {e.user_message}", 'error')
        return redirect(url_for('choose_subscription'))
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        flash('An unexpected error occurred.', 'error')
        return redirect(url_for('choose_subscription'))

    return redirect(url_for('display_journeys'))


def update_local_payment_method(user_id, exp_month, exp_year):
    """
    Updates the expiry date for the user's latest payment method in the database.

    Parameters:
        user_id (int): The ID of the user whose payment method should be updated.
        exp_month (int): The expiration month of the new payment card.
        exp_year (int): The expiration year of the new payment card.
    """
    # Retrieve the latest payment record for the user
    payment = Payment.query.filter_by(user_id=user_id).order_by(Payment.payment_date.desc()).first()
    if payment:
        payment.card_expiry_date = f"{exp_month}/{exp_year}"  # Update the card expiry date
        db.session.commit()  # Commit changes to the database
    else:
        logger.error(f"No payment record found for user ID {user_id}")  # Log error if no payment record found



@app.route('/cancel_subscription', methods=['POST'])
@login_required
@membership_required
def cancel_subscription():
    """
    Cancels the user's subscription at the end of the current billing period.
    Checks if there is an active subscription to cancel.

    Returns:
        Redirection to the index page with a status message.
    """
    user = User.query.get(current_user.id)
    if not user or not user.stripe_customer_id:
        flash('You do not have an active subscription.', 'error')  # Notify user if there is no active subscription
        return redirect(url_for('index'))

    try:
        # Retrieve the active subscription from Stripe
        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
        subscription_id = None
        for subscription in subscriptions.auto_paging_iter():
            if subscription['items']['data'][0]['price']['id'] == user.subscription_plan.stripe_price_id:
                subscription_id = subscription['id']
                break
        
        if not subscription_id:
            flash('No active subscription found for cancellation.', 'error')  # Notify if no subscription is found
            return redirect(url_for('index'))
        
        # Request cancellation of the subscription at the period's end
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        db.session.commit()  # Commit changes to the database

        flash('Your subscription will be cancelled at the end of the current billing period.', 'success')  # Notify user of successful cancellation
    except Exception as e:
        flash(f'An error occurred while cancelling your subscription: {e}', 'error')  # Show error message

    return redirect(url_for('index'))  # Redirect to the home page


@app.context_processor
def inject_subscription_details():
    """
    Context processor to inject subscription details into the template context.
    This allows subscription-related details to be available globally in all templates,
    simplifying access to current user's subscription information.

    Returns:
        dict: A dictionary containing the subscription plan name, Stripe customer ID,
              and Stripe price ID to be available in all templates.
    """
    # Default details for a user who is either not logged in or does not have a subscription
    details = {
        'subscription_plan_name': 'Not Logged In',
        'stripe_customer_id': None,
        'stripe_price_id': None
    }

    # Check if the user is authenticated
    if current_user.is_authenticated:
        user = User.query.get(current_user.id)  # Retrieve the user based on their session ID
        # Check if the user has an associated subscription plan
        if user.subscription_plan:
            # Update details with the user's subscription information
            details['subscription_plan_name'] = user.subscription_plan.plan_name
            details['stripe_customer_id'] = user.stripe_customer_id
            details['stripe_price_id'] = user.subscription_plan.stripe_price_id
        else:
            # Specify that the user is logged in but has no subscription
            details['subscription_plan_name'] = 'No Subscription'
    
    return details  # Return the details dictionary to be used in templates




@app.route('/search-users', methods=['GET'])
@login_required
@membership_required
def search_users():
    """
    Search users based on a query string and exclude the current user from the results.
    Also, check if the current user has already sent a friend request or is already friends with the user.

    Returns:
        JSON response containing HTML content to display search results and raw user data.
    """
    query = request.args.get('query', '')  # Get the search query from the request arguments
    users = User.query.filter(
        or_(User.username.ilike(f'%{query}%'), User.firstname.ilike(f'%{query}%'))  # Perform a case-insensitive like search
    ).filter(User.id != current_user.id).all()  # Exclude the current user from results

    results = []
    for user in users:
        is_friend = user in current_user.friends  # Check if the user is already a friend
        # Check for any pending friend requests from the current user to this user
        request_sent = FriendRequest.query.filter_by(
            requester_id=current_user.id,
            requestee_id=user.id,
            status='pending'
        ).first()

        # Compile user data for the response
        results.append({
            'username': user.username,
            'id': user.id,
            'request_sent': bool(request_sent),
            'can_cancel': bool(request_sent),  # Can cancel the request if it exists and is pending
            'is_friend': is_friend
        })

    html_content = render_template('searchResults.html', users=results)  # Render search results to HTML
    return jsonify(html=html_content, users=results)  # Return HTML content and user data as JSON


@app.route('/cancel-friend-request/<int:user_id>', methods=['POST'])
@login_required
@membership_required
def cancel_friend_request(user_id):
    """
    Cancels a pending friend request sent by the current user.

    Parameters:
        user_id (int): The ID of the user to whom the friend request was sent.

    Returns:
        JSON response indicating success or failure of the operation.
    """
    # Find the pending friend request to cancel
    friend_request = FriendRequest.query.filter_by(
        requester_id=current_user.id,
        requestee_id=user_id,
        status='pending'
    ).first()

    if friend_request:
        db.session.delete(friend_request)  # Delete the request if it exists and is still pending
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Friend request cancelled.'})
    else:
        return jsonify({'status': 'error', 'message': 'No pending friend request found.'}), 404


@app.route('/send-friend-request/<int:requestee_id>', methods=['POST'])
@login_required
@membership_required
def send_friend_request(requestee_id):
    """
    Sends a friend request to another user unless they are already friends or a request already exists.

    Parameters:
        requestee_id (int): The ID of the user to whom the friend request is being sent.

    Returns:
        JSON response indicating the outcome of the operation.
    """
    if current_user.id == requestee_id:
        return jsonify({'error': 'Cannot send friend request to yourself'}), 400  # Prevent self-requests
    
    potential_friend = User.query.get(requestee_id)
    if potential_friend in current_user.friends:
        return jsonify({'error': 'This user is already your friend.'}), 400  # Check if already friends

    # Check for existing outgoing or incoming friend requests
    existing_requestOut = FriendRequest.query.filter_by(
        requester_id=current_user.id, 
        requestee_id=requestee_id
    ).first()
    if existing_requestOut:
        return jsonify({'error': 'Friend request already sent.'}), 400  # Outgoing request exists
    
    existing_requestIn = FriendRequest.query.filter_by(
        requester_id=requestee_id,
        requestee_id=current_user.id
    ).first()
    if existing_requestIn:
        return jsonify({'error': 'User has already sent you a friend request.'}), 400  # Incoming request exists
    
    try:
        # Create and save the new friend request
        new_request = FriendRequest(
            requester_id=current_user.id, 
            requestee_id=requestee_id, 
            status='pending'
        )
        db.session.add(new_request)
        db.session.commit()
        return jsonify({'message': 'Friend request sent successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to send friend request: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to send friend request'}), 500


@app.route('/fetch-friend-requests', methods=['GET'])
@login_required
@membership_required
def fetch_friend_requests():
    """
    Retrieves pending friend requests sent to the current user.

    Returns:
        JSON list of pending friend requests.
    """
    incoming_requests = FriendRequest.query.filter_by(requestee_id=current_user.id, status='pending').all()  # Fetch pending requests
    requests_data = [{'id': req.id, 'username': req.requester.username} for req in incoming_requests]  # Extract data for JSON response
    return jsonify(requests_data)


@app.route('/respond-friend-request/<request_id>/<action>', methods=['POST'])
@login_required
@membership_required
def respond_friend_request(request_id, action):
    """
    Responds to a friend request by accepting or rejecting it based on the specified action.

    Parameters:
        request_id (int): The ID of the friend request.
        action (str): The action to perform ('accept' or 'reject').

    Returns:
        JSON response indicating success or the specific action taken.
    """
    friend_request = FriendRequest.query.get_or_404(request_id)  # Retrieve the friend request or return 404 if not found
    if friend_request.requestee_id != current_user.id:
        return jsonify({'error': 'This request is not for the current user.'}), 403  # Check if the request is for the current user

    if action == 'accept':
        # Add each user to the other's friends list
        requester = User.query.get(friend_request.requester_id)
        requestee = User.query.get(friend_request.requestee_id)
        requester.friends.append(requestee)
        requestee.friends.append(requester)
        friend_request.status = 'accepted'
        db.session.delete(friend_request)  # Remove the request from the database
    elif action == 'reject':
        friend_request.status = 'rejected'
        db.session.delete(friend_request)  # Remove the request from the database
    else:
        return jsonify({'error': 'Invalid action.'}), 400  # Handle invalid actions

    db.session.commit()
    return jsonify({'message': f'Friend request {action}ed successfully.'})


def unfriend(user_id, friend_id):
    """
    Removes a friend relationship between two users.

    Parameters:
        user_id (int): The ID of the current user who is initiating the unfriend action.
        friend_id (int): The ID of the user to be unfriended.

    Returns:
        bool: True if the unfriend action was successful, False otherwise.
    """
    user = User.query.get(user_id)  # Retrieve the user who is initiating the unfriend
    friend = User.query.get(friend_id)  # Retrieve the user who is to be unfriended

    if friend in user.friends:
        user.friends.remove(friend)  # Remove the friend from the user's friend list
        friend.friends.remove(user)  # Reciprocal removal from the friend's list
        db.session.commit()  # Commit changes to the database
        return True  # Return True when unfriending is successful
    return False  # Return False if the friend was not found in the user's friend list


@app.route('/unfriend/<int:friend_id>', methods=['POST'])
@login_required
@membership_required
def handle_unfriend(friend_id):
    """
    Web route to handle the unfriending of a user. This route calls the unfriend function and returns a JSON response based on the outcome.

    Parameters:
        friend_id (int): The ID of the user to unfriend.

    Returns:
        JSON response indicating whether the unfriend action was successful or not.
    """
    result = unfriend(current_user.id, friend_id)  # Call the unfriend function
    
    if result:
        return jsonify({'message': 'Friend successfully unfriended.'}), 200  # Successful unfriend
    else:
        return jsonify({'error': 'Could not unfriend the specified user.'}), 400  # Unsuccessful unfriend


@app.route('/friends')
@login_required
@membership_required
def friends():
    """
    Displays the friends and incoming friend requests of the current user. 
    Fetches data from the database and renders a template to show the information.

    Returns:
        Rendered HTML template with lists of friends and incoming friend requests.
    """
    # Fetch pending friend requests addressed to the current user
    incoming_requests = FriendRequest.query.filter_by(requestee_id=current_user.id, status='pending').all()
    friends = current_user.friends  # Retrieve the list of friends from the current user model

    # Render the 'friends.html' template, passing the friends and incoming requests to it
    return render_template('friends.html', friends=friends, requests=incoming_requests)



@app.route('/upload_gps', methods=['GET', 'POST'])
@login_required
@membership_required
def upload_gps():
    """
    Handles the upload of GPS data from users. Users can post a GPX file along with
    additional metadata about the activity.

    Returns:
        - On GET: The upload form page.
        - On POST: Redirects after attempting to process and save the uploaded GPS data.
    """
    if request.method == 'POST':
        file = request.files.get('gpsdata')
        activity_type = request.form.get('type')
        name = request.form.get('name')
        start_time_user = request.form.get('startTime')
        end_time_user = request.form.get('endTime')

        # Validate the essential inputs
        if not file or not activity_type or not name:
            flash('Missing required fields.', 'error')
            return render_template('upload_gps.html')

        try:
            # Parse the GPX file to extract GPS data
            gpx = gpxpy.parse(file.stream)
            coordinates = [{'lat': point.latitude, 'lon': point.longitude}
                           for track in gpx.tracks
                           for segment in track.segments
                           for point in segment.points]

            # Handle case where no GPS data could be extracted
            if not coordinates:
                flash('No GPS data found in file.', 'error')
                return render_template('upload_gps.html')

            # Determine start and end times of the journey
            if start_time_user and end_time_user:
                start_time = datetime.fromisoformat(start_time_user)
                end_time = datetime.fromisoformat(end_time_user)
            else:
                start_time = min((point.time for track in gpx.tracks for segment in track.segments for point in segment.points), default=datetime.utcnow())
                end_time = max((point.time for track in gpx.tracks for segment in track.segments for point in segment.points), default=datetime.utcnow())

            # Create and save the journey record
            journey = JourneyRecord(
                user_id=current_user.id,
                name=name,
                type=activity_type,
                start_time=start_time,
                end_time=end_time,
                data={'coordinates': coordinates}
            )
            db.session.add(journey)
            db.session.commit()
            flash('GPS Data successfully uploaded.', 'success')
            return redirect(url_for('display_journeys'))
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return render_template('upload_gps.html')
    else:
        return render_template('upload_gps.html')


@app.route('/journeys')
@login_required
def display_journeys():
    """
    Displays all the journeys recorded by the current user.

    Returns:
        Rendered view with a list of all user's journeys.
    """
    journeys = JourneyRecord.query.filter_by(user_id=current_user.id).all()
    return render_template('display_journey.html', journeys=journeys)


@app.route('/api/journeys')
@login_required
def api_journeys():
    """
    Provides a JSON API endpoint that returns detailed information about all the journeys recorded by the current user.
    This includes the journey's name, type, duration, distance traveled, calories burned, average speed, and the geographical data.

    Returns:
        JSON response containing a list of dictionaries, each representing details about a journey.
    """
    journeys = JourneyRecord.query.filter_by(user_id=current_user.id).all()  # Retrieve all journeys for the current user
    journeys_data = [{
        'id': journey.id,  # Unique identifier for the journey
        'name': journey.name,  # Name of the journey
        'type': journey.type,  # Type of activity (e.g., walking, cycling)
        'duration': journey.calculate_duration(),  # Calculated duration of the journey
        'distance': journey.calculate_distance(),  # Calculated distance covered in the journey
        'calories': journey.calculate_calories_burned(),  # Calculated calories burned during the journey
        'speed': journey.calculate_average_speed(),  # Calculated average speed during the journey
        'data': journey.data  # Geo-data containing coordinates
    } for journey in journeys]
    return jsonify(journeys_data)  # Return the journey data as JSON


@app.route('/api/journeys_stats')
@login_required
def api_journeys_stats():
    """
    Provides a JSON API endpoint that returns aggregated statistics about all journeys recorded by the current user.
    This includes the total calories burned, total distance covered, and the distance covered broken down by journey type.

    Returns:
        JSON response containing aggregated statistical data about the user's journeys.
    """
    user_id = current_user.id
    journeys = JourneyRecord.query.filter_by(user_id=user_id).all()  # Fetch all journeys for the current user

    total_calories = sum(journey.calculate_calories_burned() for journey in journeys)  # Sum up all calories burned
    total_distance = sum(journey.calculate_distance() for journey in journeys)  # Sum up the total distance covered

    distance_by_type = {}
    for journey in journeys:
        if journey.type in distance_by_type:
            distance_by_type[journey.type] += journey.calculate_distance()  # Add distance to existing journey type
        else:
            distance_by_type[journey.type] = journey.calculate_distance()  # Initialize distance for new journey type

    return jsonify({
        'total_calories': total_calories,  # Total calories burned
        'total_distance': total_distance,  # Total distance covered
        'distance_by_type': distance_by_type  # Distance covered by each type of journey
    })


@app.route('/list_journeys')
@login_required
def list_journeys():
    """
    Displays a list of all journeys recorded by the current user.

    Returns:
        Rendered view listing all journeys.
    """
    user_journeys = JourneyRecord.query.filter_by(user_id=current_user.id).all()
    return render_template('list_journeys.html', journeys=user_journeys)


@app.route('/list_journeys/view/<int:journey_id>')
@login_required
def view_journey(journey_id):
    """
    Displays detailed information about a specific journey.

    Parameters:
        journey_id (int): The ID of the journey to view.

    Returns:
        Rendered view with detailed information about the journey.
    """
    journey = JourneyRecord.query.get_or_404(journey_id)
    return render_template('view_journey.html', journey=journey)


@app.route('/api/journeys/<int:journey_id>')
@login_required
def api_journeys_view(journey_id):
    """
    Provides a JSON API that returns detailed information about a specific journey.

    Parameters:
        journey_id (int): The ID of the journey to view.

    Returns:
        JSON response containing detailed information about the specified journey.
    """
    journey = JourneyRecord.query.get_or_404(journey_id)
    journey_data = {
        'id': journey.id,
        'name': journey.name,
        'type': journey.type,
        'duration': journey.calculate_duration(),
        'distance': journey.calculate_distance(),
        'calories': journey.calculate_calories_burned(),
        'speed': journey.calculate_average_speed(),
        'data': journey.data
    }
    return jsonify(journey_data)


@app.route('/list_journeys/delete/<int:journey_id>', methods=['POST'])
@login_required
def delete_journey(journey_id):
    """
    Deletes a specific journey record for the current user.

    Parameters:
        journey_id (int): The ID of the journey to delete.

    Returns:
        Redirect to the list journeys page with a success or error message.
    """
    journey = JourneyRecord.query.get_or_404(journey_id)
    db.session.delete(journey)
    db.session.commit()
    flash('Journey deleted successfully.', 'success')
    return redirect(url_for('list_journeys'))


@app.route('/download_journey/<int:journey_id>', methods=['GET'])
@login_required
def download_journey(journey_id):
    """
    Provides a route for downloading a journey's details in either JSON or CSV format.
    This route checks user permissions for the journey and returns the data in the requested format.

    Parameters:
        journey_id (int): The ID of the journey to download.

    Returns:
        A downloadable file response in the specified format (JSON or CSV).
    """
    journey = JourneyRecord.query.filter_by(id=journey_id, user_id=current_user.id).first()
    if not journey:
        flash('Journey not found.', 'error')
        return redirect(url_for('list_journeys'))
    file_format = request.args.get('format', default='json')

    if file_format == 'csv':
        return download_as_csv(journey)  # Handle CSV download
    else:
        return download_as_json(journey)  # Handle JSON download as default

    

def download_as_json(journey):
    """
    Prepares and returns a JSON response with the journey details.

    Parameters:
        journey (JourneyRecord): The journey record to convert to JSON.

    Returns:
        Flask Response object with JSON data and appropriate headers for file download.
    """
    journey_details = {
        'id': journey.id,
        'name': journey.name,
        'type': journey.type,
        'start_time': journey.start_time.isoformat(),
        'end_time': journey.end_time.isoformat(),
        'duration_hours': journey.calculate_duration(),
        'distance_km': journey.calculate_distance(),
        'calories_burned': journey.calculate_calories_burned(),
        'average_speed_km_h': journey.calculate_average_speed(),
        'coordinates': journey.data.get('coordinates', [])
    }
    response = jsonify(journey_details)
    response.headers['Content-Disposition'] = f'attachment; filename=journey_{journey.id}.json'
    return response


def download_as_csv(journey):
    """
    Prepares and returns a CSV file response containing the journey details.

    Parameters:
        journey (JourneyRecord): The journey record to convert to CSV.

    Returns:
        Flask Response object with CSV data and appropriate headers for file download.
    """
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Type', 'Start Time', 'End Time', 'Duration (Hours)', 'Distance (km)', 'Calories Burned', 'Average Speed (km/h)', 'Coordinates'])
    cw.writerow([
        journey.id,
        journey.name,
        journey.type,
        journey.start_time.strftime('%Y-%m-%d %H:%M:%S'),
        journey.end_time.strftime('%Y-%m-%d %H:%M:%S'),
        f"{journey.calculate_duration():.2f}",
        f"{journey.calculate_distance():.2f}",
        f"{journey.calculate_calories_burned():.2f}",
        f"{journey.calculate_average_speed():.2f}",
        '; '.join(f"{coord['lat']},{coord['lon']}" for coord in journey.data.get('coordinates', []))
    ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=journey_{journey.id}.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@app.route('/api/friends/latest-journeys', methods=['GET'])
@login_required
@membership_required
def get_latest_journeys():
    """
    Fetches the latest journey for each friend of the current user and returns this data as JSON.
    Useful for applications displaying recent activity among friends.

    Returns:
        JSON list of the latest journeys of friends.
    """
    friends = current_user.friends
    latest_journeys = []
    for friend in friends:
        latest_journey = JourneyRecord.query.filter_by(user_id=friend.id).order_by(JourneyRecord.end_time.desc()).first()
        if latest_journey:
            latest_journeys.append({
                'user_id': friend.id,
                'username': friend.username,
                'journey_id': latest_journey.id,
                'name': latest_journey.name,
                'type': latest_journey.type,
                'duration': latest_journey.calculate_duration(),
                'distance': latest_journey.calculate_distance(),
                'calories': latest_journey.calculate_calories_burned(),
                'speed': latest_journey.calculate_average_speed(),
                'coordinates': latest_journey.data.get('coordinates', [])
            })

    return jsonify(latest_journeys)


@app.route('/view-friends-journeys')
def view_friends_journeys():
    """
    Displays a map or a list of journeys that friends have shared.
    Typically used to provide a social view of friend activities.

    Returns:
        Rendered template that integrates journey data into a map or list view.
    """
    return render_template('shared_map.html')  # Assumes a template that can display a map or list of friends' journeys
