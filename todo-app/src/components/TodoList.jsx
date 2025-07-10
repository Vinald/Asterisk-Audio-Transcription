import React from "react";
import TodoCard from "./TodoCard";

function TodoList(props) {
    const { todos } = props;
    const tab = "All";
    const filteredTodosList =
        tab === "Open"
            ? todos
            : tab === "completed"
            ? todos.filter((val) => val.complete)
            : todos.filter((val) => !val.complete);

    return (
        <>
            {filteredTodosList.map((todo, todoIndex) => {
                return <TodoCard key={todoIndex} todo={todo} />;
            })}
        </>
    );
}

export default TodoList;
