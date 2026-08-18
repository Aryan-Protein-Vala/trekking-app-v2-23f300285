# 🚀 Vue 3 Crash Course for your Viva

You are using **Vue 3 with the Composition API**. This is the modern, highly sought-after way to write Vue. Here is everything you need to know to confidently explain your frontend.

## 1. The Core Concept: Reactivity
In normal JavaScript, if you change a variable `x = 5` to `x = 10`, the HTML on your screen doesn't automatically update. You have to manually find the HTML element and inject the new number.

**Vue solves this using `ref()`.** 
When you wrap a variable in `ref()`, it becomes **Reactive**. Vue constantly watches it. If the variable changes, Vue instantly finds every place in the HTML where that variable is used and redraws it for you!

```javascript
// In app.js
const username = ref('Aryan');

// To change the value in JS, you MUST use .value
username.value = 'Protein Vala'; 
```
```html
<!-- In index.html -->
<h2>Welcome, {{ username }}</h2> 
<!-- Vue will automatically change 'Aryan' to 'Protein Vala' instantly! -->
```

## 2. `setup()` and `return`
Your entire Vue app is wrapped inside a `setup()` function. This is the engine room where you create your variables (`refs`) and write your functions (like `login` or `bookTrek`).

**The Golden Rule:** The HTML (`index.html`) is completely blind to what happens in `app.js`. If you create a variable or a function in `setup()`, the HTML cannot use it unless you explicitly export it in the `return { ... }` block at the bottom!

## 3. The 4 Magic Vue Directives (HTML Superpowers)
Vue gives your HTML tags superpowers using attributes that start with `v-`.

### ⚡ `v-if` (Conditional Rendering)
Controls whether an HTML element exists on the screen.
```html
<!-- If role is NOT 'Admin', this div is completely destroyed and removed from the screen -->
<div v-if="role === 'Admin'">
    Admin Panel
</div>
```

### ⚡ `v-model` (Two-Way Binding)
Links an `<input>` box to a `ref()` variable.
```html
<input type="text" v-model="newTrek.name">
```
* **One way:** If the user types "Himalayas" in the box, the JS variable `newTrek.name` instantly becomes "Himalayas".
* **The other way:** If your JS code randomly sets `newTrek.name.value = 'Everest'`, the text inside the input box on the screen instantly changes to "Everest".

### ⚡ `v-for` (Loops)
Loops through an array and creates a copy of the HTML element for every item.
```html
<!-- If you have 5 treks in the 'treks' array, Vue creates 5 <div> cards automatically! -->
<div v-for="trek in treks" :key="trek.id">
    <h3>{{ trek.name }}</h3>
</div>
```
*(Always include `:key` so Vue can uniquely track each card!)*

### ⚡ `@click` (Event Listeners)
This is shorthand for `v-on:click`. It listens for a mouse click and triggers a JavaScript function.
```html
<button @click="logout()">Logout</button>
```

## 4. Why use Vue instead of plain JavaScript?
If your teacher asks this, say:
*"Plain JavaScript requires you to manually select DOM elements and update their text content, which results in messy 'spaghetti code'. Vue uses a reactive Virtual DOM. I just update my state (variables) in JavaScript, and Vue automatically handles all the heavy lifting of updating the HTML efficiently."*
