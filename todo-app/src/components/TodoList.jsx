import React from "react";
import TodoCard from "./TodoCard";

function TodoList(props) {
    const { todos, selectedTab } = props;

    const filteredTodosList =
        selectedTab === "All"
            ? todos
            : selectedTab === "Open"
            ? todos.filter((val) => !val.complete)
            : todos.filter((val) => val.complete);

    return (
        <>
            {filteredTodosList.map((todo, todoIndex) => {
                return <TodoCard key={todoIndex} todoIndex={todoIndex} {...props} todo={todo} />;
            })}
        </>
    );
}

export default TodoList;
