from flask import Flask
app = Flask(__name__)

@app.route("/exchanges/:id")
def exchange():
    pass

@app.route("/exchanges/:exchange_id/pending_orders/:id")
def pending_order():
    pass

@app.route("/credits/:id")
def credit():
    pass

@app.route("/debits/:id")
def debit():
    pass

@app.route("/assets")
def assets():
    pass

@app.route("/events")
def events():
    pass

if __name__ == "__main__":
    app.run()
