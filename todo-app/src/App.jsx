import Header from "./components/Header";
import TodoList from "./components/TodoList";
import Tabs from "./components/Tabs";
import TodoInput from "./components/TodoInput";
import { useState } from "react";

function App() {
    const [todos, setTodos] = useState([{ input: "Hello! Add your first todo!", complete: true }]);

    const handleAddTodo = (input) => {
        const newTodo = { input, complete: false };
        setTodos([...todos, newTodo]);
    }

    const handleEditTodo = (index, newInput) => {

    }

    const handleDeleteTodo = (index) => {

    }
    return (
        <>
            <Header todos={todos} />
            <Tabs todos={todos} />
            <TodoList todos={todos} />
            <TodoInput handleAddTodo={handleAddTodo} />
        </>
    );
}

export default App;
