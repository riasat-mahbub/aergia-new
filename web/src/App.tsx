import { Routes, Route, Navigate } from "react-router-dom";

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/" element={<div className="p-8 text-center text-2xl font-semibold text-gray-700">Aergia CV Builder</div>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
