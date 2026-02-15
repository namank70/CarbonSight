import React, { useState } from "react";

export default function InfoTip({ text }) {
  const [open, setOpen] = useState(false);

  return (
    <span
      className="infoWrap"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onClick={() => setOpen((v) => !v)}
      role="button"
      tabIndex={0}
    >
      <span className="infoIcon">i</span>
      {open && <span className="infoBubble">{text}</span>}
    </span>
  );
}
