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
      <input type="file" @change="onFileChange" ref="fileInput" style="display: none" />
      <p v-if="!selectedFile">拖拽文件到此处，或点击选择文件</p>
      <p v-else>{{ selectedFile.name }}</p>
    </div>
    <button @click="handleUpload" :disabled="!selectedFile || isUploading" class="upload-button">
      {{ isUploading ? '上传中...' : '上传' }}
    </button>
    <div v-if="uploadStatus" class="status-message">
      <p>{{ uploadStatus }}</p>
      <p v-if="taskId">任务 ID: {{ taskId }}</p>
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
const selectedFile = ref(null);
const isUploading = ref(false);
const uploadStatus = ref('');
const taskId = ref(null);
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
    selectedFile.value = files[0];
    uploadStatus.value = '';
    taskId.value = null;
    results.value = null;
    errorDetails.value = '';
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value);
    }
  }
}

const fetchResults = async (id) => {
  try {
    const response = await axios.get(`http://localhost:8000/api/results/${id}`);
    results.value = response.data;
  } catch (error) {
    console.error('获取结果出错:', error);
    errorDetails.value = `获取结果失败: ${error.response?.data?.detail || error.message}`;
  }
};

const pollStatus = (id) => {
  pollingInterval.value = setInterval(async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/status/${id}`);
      const task = response.data;
      uploadStatus.value = `任务状态: ${task.status}`;
      if (task.status === 'completed') {
        clearInterval(pollingInterval.value);
        uploadStatus.value = '任务完成！';
        await fetchResults(id);
      } else if (task.status === 'failed') {
        clearInterval(pollingInterval.value);
        uploadStatus.value = '任务失败。';
        errorDetails.value = task.error || '未知错误';
      }
    } catch (error) {
      clearInterval(pollingInterval.value);
      console.error('轮询状态出错:', error);
      errorDetails.value = `轮询状态时出错: ${error.message}`;
    }
  }, 3000);
};

const handleUpload = async () => {
  if (!selectedFile.value) {
    return;
  }

  isUploading.value = true;
  uploadStatus.value = '正在上传文件...';
  taskId.value = null;
  results.value = null;
  errorDetails.value = '';

  const formData = new FormData();
  formData.append('file', selectedFile.value);

  try {
    const response = await axios.post('http://localhost:8000/api/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    taskId.value = response.data.task_id;
    uploadStatus.value = '文件上传成功！正在处理...';
    pollStatus(response.data.task_id);
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
  max-width: 500px;
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