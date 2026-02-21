import { useState, useRef } from 'react'

function UploadPanel({ onUpload, videoUrl }) {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const fileInputRef = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleAnalyze = () => {
    if (selectedFile) {
      onUpload(selectedFile)
    }
  }

  return (
    <div>
      <div
        className={`upload-area ${dragOver ? 'dragover' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="upload-icon">⛳</div>
        <h2>Upload Your Golf Swing Video</h2>
        <p>Drag & drop a video file here, or click to browse</p>
        <p style={{ fontSize: '0.8rem', marginTop: 8, color: '#9ca3af' }}>
          Supports MP4, MOV, AVI, WebM • Max 200MB
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {selectedFile && (
        <div className="video-preview">
          <video
            src={URL.createObjectURL(selectedFile)}
            controls
            muted
            playsInline
            style={{ pointerEvents: 'auto' }}
            onVolumeChange={(e) => { e.target.muted = true }}
          />
          <div style={{ marginTop: 12, textAlign: 'center' }}>
            <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: 12 }}>
              {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
            </p>
            <div className="actions">
              <button className="btn btn-primary" onClick={handleAnalyze}>
                🔍 Analyze Swing
              </button>
              <button className="btn btn-secondary" onClick={() => setSelectedFile(null)}>
                Clear
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UploadPanel
