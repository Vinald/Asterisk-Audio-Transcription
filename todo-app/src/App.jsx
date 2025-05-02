import "./App.css";
import Header from "./components/Header";
import TodoList from "./components/TodoList";
import Tabs from "./components/Tabs";
import TodoInput from "./components/TodoInput";

function App() {
    return (
        <>
            <Header />
            <Tabs />
            <TodoList />
            <TodoInput />
        </>
    );
}

export default App;
