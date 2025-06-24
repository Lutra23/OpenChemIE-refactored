<template>
  <div class="upload-container">
    <h2>文件上传</h2>
    <div
      class="upload-box"
      :class="{ 'drag-over': isDragging }"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @click="triggerFileInput"
    >
      <input type="file" @change="onFileChange" ref="fileInput" style="display: none" multiple />
      <div v-if="selectedFiles.length === 0">
        <p>拖拽文件到此处，或点击选择文件</p>
        <p class="small-text">(可选择多个文件)</p>
      </div>
      <div v-else>
        <p>{{ selectedFiles.length }} 个文件已选择:</p>
        <ul>
          <li v-for="file in selectedFiles" :key="file.name">{{ file.name }}</li>
        </ul>
      </div>
    </div>
    <button @click="handleUpload" :disabled="selectedFiles.length === 0 || isUploading" class="upload-button">
      {{ isUploading ? '上传中...' : '上传' }}
    </button>
    <div v-if="uploadStatus" class="status-message">
      <p>{{ uploadStatus }}</p>
      <p v-if="batchId">批处理 ID: {{ batchId }}</p>
      <p v-if="batchProgress">{{ batchProgress }}</p>
      <p v-if="errorDetails" class="error-details">{{ errorDetails }}</p>
    </div>
    <div v-if="results" class="results-container">
      <h3>提取结果</h3>
      <pre><code>{{ JSON.stringify(results, null, 2) }}</code></pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue';
import axios from 'axios';

const fileInput = ref(null);
const selectedFiles = ref([]);
const isUploading = ref(false);
const uploadStatus = ref('');
const batchId = ref(null);
const batchProgress = ref('');
const isDragging = ref(false);
const results = ref(null);
const pollingInterval = ref(null);
const errorDetails = ref('');

const triggerFileInput = () => {
  fileInput.value.click();
};

const onFileChange = (event) => {
  handleFile(event.target.files);
};

const onDragEnter = () => {
  isDragging.value = true;
};

const onDragLeave = () => {
  isDragging.value = false;
};

const onDrop = (event) => {
  isDragging.value = false;
  handleFile(event.dataTransfer.files);
};

const handleFile = (files) => {
  if (files.length > 0) {
    selectedFiles.value = Array.from(files);
    uploadStatus.value = '';
    batchId.value = null;
    batchProgress.value = '';
    results.value = null;
    errorDetails.value = '';
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value);
    }
  }
}

const fetchResults = async (id) => {
  try {
    const response = await axios.get(`http://localhost:8000/api/results/batch/${id}`);
    results.value = response.data;
  } catch (error) {
    console.error('获取结果出错:', error);
    errorDetails.value = `获取结果失败: ${error.response?.data?.detail || error.message}`;
  }
};

const pollStatus = (id) => {
  pollingInterval.value = setInterval(async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/status/batch/${id}`);
      const task = response.data;
      uploadStatus.value = `批处理状态: ${task.status}`;
      batchProgress.value = `${task.completed_files} / ${task.total_files} 文件已完成 (失败: ${task.failed_files})`;
      
      if (task.status === 'completed' || task.status === 'failed') {
        clearInterval(pollingInterval.value);
        uploadStatus.value = '批处理完成！';
        if (task.completed_files > 0) {
            await fetchResults(id);
        }
      }
    } catch (error) {
      clearInterval(pollingInterval.value);
      console.error('轮询状态出错:', error);
      errorDetails.value = `轮询状态时出错: ${error.message}`;
    }
  }, 3000);
};

const handleUpload = async () => {
  if (selectedFiles.value.length === 0) {
    return;
  }

  isUploading.value = true;
  uploadStatus.value = '正在上传文件...';
  batchId.value = null;
  batchProgress.value = '';
  results.value = null;
  errorDetails.value = '';

  const formData = new FormData();
  selectedFiles.value.forEach(file => {
    formData.append('files', file);
  });

  try {
    const response = await axios.post('http://localhost:8000/api/upload/batch/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    batchId.value = response.data.batch_id;
    uploadStatus.value = '文件上传成功！正在处理...';
    pollStatus(response.data.batch_id);
  } catch (error) {
    console.error('上传出错:', error);
    if (error.response) {
      uploadStatus.value = `上传失败: ${error.response.data.detail || error.response.statusText}`;
    } else {
      uploadStatus.value = `上传失败: ${error.message}`;
    }
  } finally {
    isUploading.value = false;
  }
};

onUnmounted(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
  }
});
</script>

<style scoped>
.upload-container {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  border: 1px solid #ccc;
  border-radius: 8px;
  text-align: center;
}

.upload-box {
  margin-top: 1.5rem;
  padding: 2rem;
  border: 2px dashed #ccc;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s, border-color 0.3s;
}

.upload-box:hover, .upload-box.drag-over {
  background-color: #f0f7ff;
  border-color: #4285f4;
}

.upload-box p {
  margin: 0;
  color: #666;
}

.upload-box ul {
  list-style-type: none;
  padding: 0;
  margin-top: 0.5rem;
  max-height: 150px;
  overflow-y: auto;
  font-size: 0.9em;
}

.small-text {
    font-size: 0.8rem;
    color: #999;
}

.upload-button {
  margin-top: 1.5rem;
}

button {
  padding: 0.5rem 1rem;
  border: 1px solid transparent;
  border-radius: 4px;
  background-color: #42b983;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  background-color: #33a06f;
}

.status-message {
  margin-top: 1.5rem;
  padding: 1rem;
  border-radius: 4px;
  background-color: #f0f0f0;
  text-align: left;
}

.error-details {
  color: #d9534f;
  margin-top: 0.5rem;
  font-weight: bold;
}

.results-container {
  margin-top: 2rem;
  padding: 1.5rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
  text-align: left;
}

.results-container h3 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.results-container pre {
  background-color: #2d2d2d;
  color: #f0f0f0;
  padding: 1rem;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
}
</style> 