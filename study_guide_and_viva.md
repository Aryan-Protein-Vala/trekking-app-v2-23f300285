# 🎓 Trekking App V2 - Study Guide & Viva Prep

This guide is designed to help you prepare for your viva. We have successfully injected deep, educational comments into both `index.html` and `app.js` in the `trekking_app_23f3000285` folder. Please review those files line-by-line—they are now your textbook for Vue.js and frontend integration!

---

## 🏗️ The Big Picture: How Data Flows (Architecture)

Since you used AI to build this, it's totally normal to feel lost in the structure. Here is how your app's pieces talk to each other:

1. **The Database (SQLite) & Models (`models.py`)**: This is the foundation. It dictates *how* data is structured. `models.py` creates the blueprints (Users, Treks, Bookings).
2. **The Backend API (`app.py`)**: This is the bridge. It connects the Database to the outside world. It defines "routes" (like `/api/treks`). When a request hits a route, `app.py` uses the models to fetch/save data, and then returns JSON.
3. **The Frontend JS (`app.js`)**: This is the messenger. It uses `fetch()` to call the routes in `app.py`. It takes the JSON data (e.g., a list of treks) and stores it in Vue's **Reactive State** variables (like `treks.value = ...`).
4. **The Frontend UI (`index.html`)**: This is the face. It reads the variables from `app.js` and draws the screen using Vue directives (like `v-for="trek in treks"`). If the user clicks a button, the HTML triggers a function in `app.js`, which calls `app.py`, which updates `models.py`.

---

## 🪟 How to "Turn It On" in Windows

Windows requires a few extra steps for Redis and Celery to run properly, because they were originally built for Linux!

### Step 1: Install `gevent` for Celery
Celery does not officially support Windows natively. If you try to run it normally, it might crash or hang. You need an execution pool called `gevent`.
Run this in your terminal:
```bash
pip install gevent
```

### Step 2: Running Redis on Windows (WSL)
You installed Redis correctly in WSL! If you see **"Address already in use"**, that means **Redis is already running successfully in the background!** (Ubuntu automatically starts the Redis service when you install it). 
You don't need to do anything else for Redis—it's working perfectly.

### Step 3: Starting the Servers (Open 3 Terminals)

> [!IMPORTANT]
> **YOU MUST BE IN THE `backend` FOLDER BEFORE RUNNING THESE COMMANDS!** 
> If you are in the wrong folder, you will get a `ModuleNotFoundError: No module named 'app'`.

**Terminal 1: Start the Flask Server**
```bash
cd trekking_app_23f3000285/backend
python app.py
```

**Terminal 2: Start the Celery Worker (Windows specific command)**
```bash
cd trekking_app_23f3000285/backend
celery -A app.celery_app worker --loglevel=info -P gevent
```

**Terminal 3: Start the Celery Beat (for scheduled tasks)**
```bash
cd trekking_app_23f3000285/backend
celery -A app.celery_app beat --loglevel=info
```

---

## 📚 Teaching you Flask & SQLAlchemy from 0

You asked how Flask and SQLAlchemy work from scratch. Here is the absolute simplest explanation.

### What is Flask?
Flask is just a Python program that listens for HTTP requests (like when you type a URL into a browser). 
Normally, a Python script runs from top to bottom and exits. Flask uses `app.run()` to stay open in a loop, listening on a port (like 5000).

When someone visits a URL, Flask looks for a function labeled with a matching `@app.route()`.
```python
@app.route('/hello')
def say_hello():
    return "Hello World!"
```
When you go to `localhost:5000/hello`, Flask literally just runs the `say_hello()` function and sends the returned string back to the browser. In your app, instead of returning strings, you return JSON dictionaries (`jsonify()`), which `app.js` can read.

### What is SQLAlchemy?
If you want to save data, you need a database (like SQLite). Normally, you have to write SQL strings:
`db.execute("INSERT INTO user (username, password) VALUES ('aryan', '123')")`

This is messy. SQLAlchemy is an **ORM (Object Relational Mapper)**. It maps a database table to a Python Class.
Instead of writing SQL, you write Python:
```python
# 1. Create a new user object
new_user = User(username='aryan', password='123')

# 2. Add it to the "staging area" (the session)
db.session.add(new_user)

# 3. Commit it! This translates the Python object into an SQL INSERT statement behind the scenes.
db.session.commit()
```

To fetch data, instead of `SELECT * FROM trek`, you do:
```python
all_treks = Trek.query.all()
# Returns a Python list of Trek objects!
```
It makes talking to the database feel exactly like normal Python programming.

---

## 🎯 Viva Preparation: Expected Questions

### Conceptual Questions

1. **"Explain the difference between Two-Way Data Binding and One-Way Data Flow."**
   - **Answer**: Two-way binding (like `v-model` in Vue) means if the user types in an input box, the JS variable updates, and if JS updates the variable, the input box updates. One-way data flow (like passing props) means data only flows downwards from a parent to a child.
   
2. **"Why are you using `async/await` for your `fetch()` calls?"**
   - **Answer**: Network requests are asynchronous. If we didn't wait, the JS engine would move to the next line before the server responds, resulting in `undefined` data. `await` pauses the function execution until the Promise resolves, without freezing the entire browser.

3. **"How does the backend know who is making the request to book a trek?"**
   - **Answer**: We use JWT (JSON Web Tokens). Upon login, the backend issues a token. The frontend stores it in `localStorage` and sends it in the HTTP headers (`Authorization: Bearer <token>`) for protected requests. The backend decodes this token using `@jwt_required()` to get the user's identity.

4. **"Why use Celery for the CSV export instead of just generating it directly in the Flask route?"**
   - **Answer**: If the database is huge, generating a CSV takes time. If we do it in the Flask route, the user's browser will hang waiting for a response, and the server thread is blocked. Celery handles it in the background while Flask immediately returns a "Task Started" (HTTP 202) response.

5. **"What is Redis doing in your application?"**
   - **Answer**: It serves two purposes. First, it acts as a **Message Broker** for Celery to queue tasks. Second, it acts as a **Cache**. In `get_treks()`, we cache the treks array in Redis for 60 seconds (`redis_client.setex`) to reduce database load.

### Practical Code Questions (Be ready to code these!)

> [!WARNING]
> Your teacher might ask you to make a small change live to prove you wrote the code. Be prepared for these scenarios:

**1. "Add a feature to clear the search/cache."**
- *How to do it:* You'd add a button in `index.html` with `@click="clearCache"`. In `app.js`, you'd add a `clearCache` async function that makes a `DELETE` request to a new Flask route which calls `redis_client.delete('all_treks')`.

**2. "Can you modify the `v-for` loop so it only shows Treks with a difficulty of 'Hard'?"**
- *How to do it:* In `index.html`, inside the `v-for="trek in treks"` block, add a `v-if`:
  ```html
  <div v-for="trek in treks" :key="trek.id" class="col-md-4 mb-3" v-if="trek.difficulty === 'Hard'">
  ```
  *(Or better yet, create a `computed` property in `app.js` that filters the treks).*

**3. "Show me what happens if the backend server crashes when you click Login."**
- *How to explain it:* The `fetch()` call will throw a network error. Currently, your `try/catch` is missing around the `fetch` in `app.js`, so it will fail silently in the console. 
- *How to fix it:* Wrap the `fetch` in a `try { ... } catch (err) { errorMsg.value = "Server is down"; }`.
