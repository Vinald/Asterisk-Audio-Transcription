import React from "react";

function Buttons() {
    const handleClick = () => {
        alert("Button clicked!");
    };
    const handleMouseOver = () => {
        alert("Mouse over button!");
    };
    const doubleClick = () => {
        alert("Button double clicked!");
    };
    return (
        <div>
            <button onClick={handleClick}>Click Me</button>
            <button onMouseOver={handleMouseOver}>Hover Over Me</button>
            <button onDoubleClick={doubleClick}>Double Click Me</button>
        </div>
    )
}

export default Buttons;
