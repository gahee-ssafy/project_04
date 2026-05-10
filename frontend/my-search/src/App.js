import { useState, useRef } from "react";

const API_BASE = "http://localhost:8000/api/v1";

const torn = {
  background: "#f0f0f0",
  borderRadius: "2px",
  clipPath: "polygon(0% 8%, 2% 0%, 5% 6%, 8% 1%, 11% 7%, 14% 2%, 17% 8%, 20% 1%, 23% 6%, 26% 0%, 29% 7%, 32% 2%, 35% 8%, 38% 1%, 41% 6%, 44% 0%, 47% 7%, 50% 2%, 53% 8%, 56% 1%, 59% 6%, 62% 0%, 65% 7%, 68% 2%, 71% 8%, 74% 1%, 77% 6%, 80% 0%, 83% 7%, 86% 2%, 89% 8%, 92% 1%, 95% 6%, 98% 0%, 100% 8%, 100% 92%, 98% 100%, 95% 94%, 92% 100%, 89% 93%, 86% 100%, 83% 94%, 80% 100%, 77% 93%, 74% 100%, 71% 94%, 68% 100%, 65% 93%, 62% 100%, 59% 94%, 56% 100%, 53% 93%, 50% 100%, 47% 94%, 44% 100%, 41% 93%, 38% 100%, 35% 94%, 32% 100%, 29% 93%, 26% 100%, 23% 94%, 20% 100%, 17% 93%, 14% 100%, 11% 94%, 8% 100%, 5% 93%, 2% 100%, 0% 92%)",
};

export default function App() {
  const [query, setQuery] = useState("");
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(null);
  const fileRef = useRef();

  const handleImage = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImage(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview(null);
    fileRef.current.value = "";
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setAnswer("");
    setSources([]);
    setElapsed(null);

    try {
      let response;
      if (image) {
        const formData = new FormData();
        formData.append("query", query);
        formData.append("image", image);
        response = await fetch(`${API_BASE}/search/image/`, { method: "POST", body: formData });
      } else {
        response = await fetch(`${API_BASE}/search/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "sources") setSources(data.data);
            if (data.type === "chunk") setAnswer(p => p + data.text);
            if (data.type === "done") setElapsed(data.elapsed);
          } catch {}
        }
      }
    } catch {
      setAnswer("❌ 오류가 발생했어요. 서버를 확인해주세요.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSearch(); }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#ffffff", fontFamily: "'Segoe UI', sans-serif" }}>
      <div style={{ maxWidth: 780, margin: "0 auto", padding: "64px 24px" }}>

        {/* 헤더 */}
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <h1 style={{ fontSize: 36, fontWeight: 800, color: "#5B5BD6", margin: 0, letterSpacing: -1 }}>
            AI 검색엔진
          </h1>
          <p style={{ color: "#aaa", marginTop: 10, fontSize: 14 }}>텍스트 또는 이미지로 검색해보세요</p>
        </div>

        {/* 이미지 미리보기 */}
        {imagePreview && (
          <div style={{ marginBottom: 20, position: "relative", display: "inline-block" }}>
            <img src={imagePreview} alt="preview"
              style={{ maxHeight: 140, borderRadius: 8, border: "1px solid #e0e0e0" }} />
            <button onClick={removeImage} style={{
              position: "absolute", top: -8, right: -8,
              background: "#ef4444", color: "#fff", border: "none",
              borderRadius: "50%", width: 22, height: 22, cursor: "pointer", fontSize: 13
            }}>×</button>
          </div>
        )}

        {/* 검색창 - 찢어진 종이 스타일 */}
        <div style={{ display: "flex", alignItems: "stretch", gap: 16, marginBottom: 16 }}>

          {/* query 입력 */}
          <div style={{ flex: 1, ...torn, padding: "18px 28px", position: "relative" }}>
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="검색어를 입력하세요..."
              rows={1}
              style={{
                width: "100%", border: "none", background: "transparent",
                fontSize: 18, fontWeight: 700, color: "#5B5BD6",
                resize: "none", outline: "none", boxSizing: "border-box",
                fontFamily: "inherit",
              }}
            />
          </div>

          {/* 질문 버튼 */}
          <div
            onClick={!loading && query.trim() ? handleSearch : undefined}
            style={{
              background: "#f0f0f0",
              padding: "18px 24px",
              cursor: loading || !query.trim() ? "not-allowed" : "pointer",
              border: "2.5px solid #5B5BD6",
              borderRadius: "0px",
              boxSizing: "border-box",
              minWidth: 100,
              textAlign: "center",
              color: loading ? "#aaa" : "#5B5BD6",
              fontWeight: 700,
              fontSize: 16,
              userSelect: "none",
              transition: "all 0.2s",
            }}
          >
            {loading ? "..." : "질문"}
          </div>
        </div>

        {/* 이미지 첨부 버튼 */}
        <div style={{ marginBottom: 32 }}>
          <button onClick={() => fileRef.current.click()} style={{
            background: "none", border: "1.5px dashed #ccc", borderRadius: 8,
            padding: "7px 16px", cursor: "pointer", color: "#999", fontSize: 13
          }}>
            📎 {image ? image.name : "이미지 첨부"}
          </button>
          <input ref={fileRef} type="file" accept="image/*" onChange={handleImage} style={{ display: "none" }} />
        </div>
        {sources.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <p style={{ fontSize: 12, color: "#aaa", fontWeight: 600, marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
              🔗 참고 소스
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {sources.map((s, i) => (
                <a key={i} href={s.url} target="_blank" rel="noreferrer" style={{
                  background: "#f8f8f8", borderRadius: 8, padding: "10px 16px",
                  textDecoration: "none", color: "#333", fontSize: 14,
                  display: "flex", alignItems: "center", gap: 10,
                  border: "1px solid #eee"
                }}>
                  <span style={{ color: "#5B5BD6", fontWeight: 700 }}>[{s.rank}]</span>
                  {s.title}
                </a>
              ))}
            </div>
          </div>
        )}

        {/* 답변 */}
        {(answer || loading) && (
          <div style={{ ...torn, padding: "28px 32px", borderLeft: "4px solid #5B5BD6" }}>
            <p style={{ fontSize: 12, color: "#5B5BD6", fontWeight: 600, margin: "0 0 14px", textTransform: "uppercase", letterSpacing: 1 }}>
              ✨ AI 답변
            </p>
            <p style={{ color: "#333", lineHeight: 1.9, margin: 0, whiteSpace: "pre-wrap", fontSize: 15 }}>
              {answer}
              {loading && <span style={{
                display: "inline-block", width: 9, height: 16,
                background: "#5B5BD6", marginLeft: 3, borderRadius: 2,
                animation: "blink 1s infinite"
              }} />}
            </p>
            {elapsed && <p style={{ color: "#bbb", fontSize: 12, marginTop: 14, marginBottom: 0 }}>⏱ {elapsed}초</p>}
          </div>
        )}
      </div>

      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
    </div>
  );
}