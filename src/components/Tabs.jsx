import React from "react";

function Tabs(props) {
    const { todos, selectedTab, setSelectedTab } = props;
    const tabs = ["All", "Open", "Complete"];

    return (
        <nav className="tab-container">
            {tabs.map((tab, tabIndex) => {
                const numOfTasks =
                    tab === "All"
                        ? todos.length
                        : tab === "Open"
                        ? todos.filter((val) => !val.complete).length
                        : todos.filter((val) => val.complete).length;

                return (
                    <button
                        key={tabIndex}
                        className={"tab-button " + (selectedTab === tab ? "tab-selected" : "")}
                        onClick={() => setSelectedTab(tab)}
                    >
                        <h4>
                            {tab} <span>({numOfTasks})</span>
                        </h4>
                    </button>
                );
            })}
            <hr />
        </nav>
    );
}

export default Tabs;
