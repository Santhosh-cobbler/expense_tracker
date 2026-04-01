from flask import Flask, render_template, redirect, url_for, session, request
from dotenv import load_dotenv
import os

# Supabase
from supabase import Client, create_client

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

app = Flask(__name__)



#supabase connectivity
supabase: Client = create_client(
    SUPABASE_URL,SUPABASE_KEY
)

app.secret_key = 'supersecretkey'


#switchboard
@app.route('/')
def switchboard():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    return redirect(url_for('login'))


@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_data = supabase.auth.get_user()

    if user_data and user_data.user:
        #access the meta data
        user_name = user_data.user.user_metadata.get('name','Guest')

        credit_response = supabase.table('income').select('*').eq('user_id',session['user_id']).execute()
        debit_response = supabase.table('expenses').select('*').eq('user_id',session['user_id']).execute()

        #calculating total credited amount
        credit_amt = credit_response.data
        credit_amt = sum(item['amount']for item in credit_amt)

        # calculating total debited amount
        debit_amt = debit_response.data
        debit_amt = sum(dt_item['amount']for dt_item in debit_amt)

    else:
        # if supabase doesn't recoganize the session then it redirects to login
        session.clear()
        return redirect(url_for('login'))

    return render_template('home.html', user_name=user_name, credit_past =credit_amt, debit_past=debit_amt)


#register-form
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # supabase going to create the new user
        response = supabase.auth.sign_up({
            "email":email,
            "password": password,
            "options":{
                "data":{
                    "name":name
                }
            }
        })

        if response.user:
            return(redirect(url_for('login')))
        
        else:
            return "Reistration failed"

    return render_template('register.html')


#login-form
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            data = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            #supabase session data
            session['supabase_session'] = data.session.access_token

            # flask session
            session['user_id'] = data.user.id

            return redirect(url_for('home'))

        except Exception as e:
            return f"Login failed {str(e)}"

    return render_template('login.html')

#credit-form
@app.route('/credit', methods=['GET','POST'])
def credit():
    token = session.get('supabase_session')

    #if user_doesn't login
    if not token:
        return redirect(url_for('login'))
    
    # manually set the header
    supabase.postgrest.auth(token)

    if request.method == 'POST':
        source = request.form.get('source')
        amount = request.form.get('amount')
        deposited_on = request.form.get('account')
        date = request.form.get('date')

        
        '''connection to supabase'''
        data = {
            'user_id':session['user_id'],
            'source':source,
            'amount':amount,
            'account':deposited_on,
            'date':date
        }
        try:
            # if token is the header then insert will happen
            supabase.table('income').insert(data).execute()
            return render_template('credit.html')
        
        except Exception as e:
            return f'Database error: {str(e)}'

    return render_template('credit.html')

@app.route('/debit', methods=['GET','POST'])
def debit():
    # session of supabase
    token = session.get('supabase_session')
    user_id = session.get('user_id')
    # user doesn't login it redirects to login
    if not token or not user_id:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        items = request.form.get('item')
        cat = request.form.get('category')
        amt = request.form.get('amount')
        date = request.form.get('date')

        data = {
            
            'user_id': session['user_id'],
            'item': items,
            'category': cat,
            'amount': amt,
            'date':date
            
        }
        
        try:
            #insert data into supabase
            supabase.table('expenses').insert(data).execute()

        except Exception as e:
            return f"Database error: {str(e)}"
    return render_template('debit.html')


'''
    First add the credit and debit stuff on the supabase then you can 
    add the view connection the application
'''

@app.route('/credit-view')
def credit_view():
    # checks the users
    if 'user_id' not in session:
        return redirect(url_for('login'))

    token = session.get('supabase_session')
    if token:
        supabase.postgrest.auth(token)

    response = supabase.table('income').select('*').eq('user_id',session['user_id']).execute()
    income_details = response.data

    return render_template('credit-view.html', data=income_details)


@app.route('/debit-view')
def debit_view():
    # checks the users
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    token = session.get('supabase_session')
    if token:
        supabase.postgrest.auth(token)

    response = supabase.table('expenses').select('*').eq('user_id',session['user_id']).execute()
    expense_details = response.data
    
    return render_template('debit-view.html',data=expense_details)

if __name__ == '__main__':
    app.run()
