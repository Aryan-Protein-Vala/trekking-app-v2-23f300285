// Vue 3 Composition API: We extract the functions we need from the global Vue object.
// createApp: Bootstraps the Vue application.
// ref: Makes a variable "reactive" (if it changes, the UI updates automatically).
// onMounted: A lifecycle hook that runs when the component is first added to the DOM.
const { createApp, ref, onMounted } = Vue;

// The base URL for our backend API. Since the frontend and backend run on the same server in development, 
// '/api' is a relative path that points to 'http://localhost:5000/api'.
const API_URL = '/api';

createApp({
    setup() {
        // --- REACTIVE STATE VARIABLES ---
        // These variables hold the data for our application. Because they are wrapped in ref(),
        // Vue is watching them. Whenever we update them (e.g., token.value = 'abc'), Vue re-renders the relevant parts of the HTML.

        // We try to get the JWT token and user role from the browser's localStorage. 
        // This ensures the user stays logged in even if they refresh the page.
        const token = ref(localStorage.getItem('token') || '');
        const role = ref(localStorage.getItem('role') || '');
        
        // This object is bound (using v-model) to the username and password input fields in the HTML.
        const loginData = ref({ username: '', password: '' });
        
        // Holds error messages (like "Invalid password") to display in a red alert box.
        const errorMsg = ref('');
        
        // An array that will hold all the trek objects fetched from the backend database.
        const treks = ref([]);
        
        // Bound to the inputs in the Admin's "Create Trek" form.
        const newTrek = ref({ name: '', location: '', difficulty: '', duration_days: null, available_slots: null });
        
        // Used by Staff when editing a trek. When a trek is selected, this becomes an object; otherwise it's null.
        const selectedTrek = ref(null);
        
        // Holds the URL for the downloadable CSV file after a User requests an export.
        const exportLink = ref('');

        // --- ASYNC FUNCTIONS ---
        // We use async/await because network requests take time. We don't want the browser to freeze while waiting.

        // Fetches the list of all treks from the backend.
        // ---> CROSS-REFERENCE: This calls the `def get_treks()` function in `app.py` mapped to `@app.route('/api/treks')`.
        const fetchTreks = async () => {
            // We must send the token if we have one, otherwise the backend doesn't know who we are!
            const headers = token.value ? { 'Authorization': `Bearer ${token.value}` } : {};
            const res = await fetch(`${API_URL}/treks`, { headers });
            treks.value = await res.json(); // Parses the JSON response and updates the reactive array
        };

        // Handles user login
        // ---> CROSS-REFERENCE: This calls the `def login()` function in `app.py` mapped to `@app.route('/api/login')`.
        // ---> It checks the `User` model in `models.py` to verify the username and password.
        const login = async () => {
            const res = await fetch(`${API_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }, // Tell the server we are sending JSON data
                body: JSON.stringify(loginData.value) // Convert our JS object into a JSON string
            });
            const data = await res.json();
            
            if (res.ok) { // HTTP status is 2xx (Success)
                token.value = data.token; // Update reactive state
                role.value = data.role;
                
                // Save token and role to localStorage for persistence across page reloads
                localStorage.setItem('token', token.value);
                localStorage.setItem('role', role.value);
                
                errorMsg.value = ''; // Clear any previous errors
                fetchTreks(); // Load the treks now that the user is authenticated
            } else { // HTTP status is 4xx or 5xx (Error)
                errorMsg.value = data.msg; // Show the error message returned by the server
            }
        };

        // Handles user registration
        // ---> CROSS-REFERENCE: This calls the `def register()` function in `app.py` mapped to `@app.route('/api/register')`.
        // ---> It inserts a new row into the `User` model in `models.py`.
        const register = async () => {
            const res = await fetch(`${API_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // We use the spread operator (...) to copy username and password from loginData, 
                // and we force the role to always be 'User' for new registrations.
                body: JSON.stringify({ ...loginData.value, role: 'User' })
            });
            if (res.ok) {
                alert('Registered! You can now login.');
            } else {
                const data = await res.json();
                errorMsg.value = data.msg;
            }
        };

        // Handles logging out (purely client-side logic)
        const logout = () => {
            token.value = ''; // Clear reactive state
            role.value = '';
            localStorage.removeItem('token'); // Remove from browser storage
            localStorage.removeItem('role');
        };

        // Admin function to create a new trek
        // ---> CROSS-REFERENCE: This calls `def create_trek()` in `app.py` mapped to `@app.route('/api/admin/treks')`.
        // ---> It inserts a new row into the `Trek` model in `models.py`.
        const createTrek = async () => {
            const res = await fetch(`${API_URL}/admin/treks`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    // Protected routes require the JWT token in the Authorization header
                    'Authorization': `Bearer ${token.value}` 
                },
                body: JSON.stringify(newTrek.value)
            });
            if (res.ok) {
                // Reset the form fields to blank after a successful creation
                newTrek.value = { name: '', location: '', difficulty: '', duration_days: null, available_slots: null };
                fetchTreks(); // Refresh the trek list to show the newly created trek
            }
        };

        // Staff function to update a trek's status or slots
        // ---> CROSS-REFERENCE: This calls `def update_trek(trek_id)` in `app.py` mapped to `@app.route('/api/staff/treks/<int:trek_id>')`.
        const updateTrek = async () => {
            // Notice how we dynamically insert the trek ID into the URL string using template literals `${}`
            const res = await fetch(`${API_URL}/staff/treks/${selectedTrek.value.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
                // We only send the fields that need updating
                body: JSON.stringify({ status: selectedTrek.value.status, available_slots: selectedTrek.value.available_slots })
            });
            if (res.ok) {
                selectedTrek.value = null; // Close the edit form
                fetchTreks(); // Refresh the list to reflect changes
            }
        };

        // User function to book a trek
        // ---> CROSS-REFERENCE: This calls `def book_trek()` in `app.py` mapped to `@app.route('/api/user/book')`.
        // ---> It creates a new `Booking` in `models.py` linking the User and Trek.
        const bookTrek = async (id) => {
            const res = await fetch(`${API_URL}/user/book`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` },
                body: JSON.stringify({ trek_id: id })
            });
            if (res.ok) {
                alert('Successfully Booked!');
                fetchTreks(); // Refresh to update the available slots count
            } else {
                alert('Failed to book trek.');
            }
        };

        const cancelBooking = async (id) => {
            const res = await fetch(`${API_URL}/user/cancel/${id}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` }
            });
            if (res.ok) {
                alert('Booking cancelled successfully!');
                fetchTreks();
            } else {
                alert('Failed to cancel booking.');
            }
        };

        // User function to export their bookings to a CSV file (triggering a background task)
        // ---> CROSS-REFERENCE: This calls `def export_bookings()` in `app.py` mapped to `@app.route('/api/user/export')`.
        // ---> It triggers the Celery background task `@celery_app.task(name='app.export_bookings_csv')` defined in `app.py`.
        const exportBookings = async () => {
            const res = await fetch(`${API_URL}/user/export`, {
                method: 'POST',
                // No body needed, just the authentication token so the server knows WHO is exporting
                headers: { 'Authorization': `Bearer ${token.value}` }
            });
            if (res.ok) {
                const data = await res.json();
                // Build the URL to access the generated static file
                exportLink.value = `/static/exports/${data.filename}`;
                alert('Export started! Your download link will appear in a moment.');
            } else {
                alert('Export failed.');
            }
        };

        // --- ADMIN STATS ---
        // Holds the total number of treks.
        const totalTreksCount = ref(0);

        // Fetches statistics from the backend (Admin only).
        const fetchStats = async () => {
            const res = await fetch(`${API_URL}/stats`, {
                headers: { 'Authorization': `Bearer ${token.value}` }
            });
            if (res.ok) {
                const data = await res.json();
                totalTreksCount.value = data.total_treks;
            }
        };

        // --- INITIALIZATION ---
        // If the token is already present (e.g., user just refreshed the page and it was loaded from localStorage),
        // fetch the treks immediately so the dashboard populates.
        if (token.value) {
            fetchTreks();
            if (role.value === 'Admin') fetchStats();
        }

        // --- RETURN OBJECT ---
        // EVERYTHING you want to use in the HTML template (index.html) MUST be returned here.
        // If a variable or function isn't returned, the HTML cannot see it.
        return { 
            token, role, loginData, errorMsg, treks, newTrek, selectedTrek, exportLink, totalTreksCount,
            login, register, logout, createTrek, updateTrek, bookTrek, exportBookings, cancelBooking, fetchStats 
        };
    }
}).mount('#app'); // Tells Vue to take control of the <div id="app"> element in the HTML

