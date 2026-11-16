import { Route, Routes } from "react-router-dom";
import { HOME_URL, PRODUCT_URL } from "./types";
import { Shelf } from "./Shelf";
import { Study } from "./Study";

export function App() {
  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href={HOME_URL}>
          <span className="mark" aria-hidden="true" />
          Lynote
        </a>
        <span className="edition">Learning Path · Open edition</span>
        <a className="text-link product-link" href={PRODUCT_URL}>
          Full product
        </a>
      </header>
      <Routes>
        <Route path="/" element={<Shelf />} />
        <Route path="/course/:courseId" element={<Study />} />
      </Routes>
    </div>
  );
}
