export default function handler(_req, res) {
  res.status(410).json({
    error: "This legacy chat endpoint has been retired. Use the Flask backend's /api/chat endpoint.",
  });
}
