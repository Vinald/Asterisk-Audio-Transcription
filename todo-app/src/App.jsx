import Header from "./components/Header";
import TodoList from "./components/TodoList";
import Tabs from "./components/Tabs";
import TodoInput from "./components/TodoInput";
import { useState } from "react";

function App() {
    const [todos, setTodos] = useState([{ input: "Hello! Add your first todo!", complete: true }]);
    const [selectedTab, setSelectedTab] = useState("Open");

    const handleAddTodo = (input) => {
        const newTodo = { input, complete: false };
        setTodos([...todos, newTodo]);
    };

    const handleCompleteTodo = (index) => {
        const updatedTodos = todos.map((todo, i) =>
            i === index ? { ...todo, complete: !todo.complete } : todo
        );
        setTodos(updatedTodos);
    };

    const handleDeleteTodo = (index) => {
        const newTodoList = todos.filter((_, i) => i !== index);
        setTodos(newTodoList);
    };
    return (
        <>
            <Header todos={todos} />
            <Tabs todos={todos} selectedTab={selectedTab} setSelectedTab={setSelectedTab} />
            <TodoList
                todos={todos}
                selectedTab={selectedTab}
                handleCompleteTodo={handleCompleteTodo}
                handleDeleteTodo={handleDeleteTodo}
            />
            <TodoInput handleAddTodo={handleAddTodo} />
        </>
    );
}

export default App;
