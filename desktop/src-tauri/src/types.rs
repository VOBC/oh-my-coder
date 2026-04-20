use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

/// Server 连接配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub api_key: Option<String>,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".to_string(),
            port: 8080,
            api_key: None,
        }
    }
}

impl ServerConfig {
    pub fn base_url(&self) -> String {
        format!("http://{}:{}", self.host, self.port)
    }
}

/// 任务提交请求
#[derive(Debug, Serialize)]
pub struct RunRequest {
    pub prompt: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HashMap<String, String>>,
}

/// 任务响应
#[derive(Debug, Deserialize, Clone)]
pub struct TaskResponse {
    pub task_id: String,
    pub status: String,
    pub created_at: String,
    pub prompt: String,
    #[serde(default)]
    pub started_at: Option<String>,
    #[serde(default)]
    pub completed_at: Option<String>,
    #[serde(default)]
    pub execution_time: f64,
    #[serde(default)]
    pub metadata: HashMap<String, String>,
}

/// 任务结果
#[derive(Debug, Deserialize, Clone)]
pub struct TaskResult {
    pub task_id: String,
    pub status: String,
    pub result: Option<TaskOutput>,
    pub error: Option<String>,
    pub execution_time: f64,
    pub completed_at: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct TaskOutput {
    pub output: String,
    pub status: String,
}

/// 任务列表
#[derive(Debug, Deserialize)]
pub struct TaskListResponse {
    pub total: usize,
    pub tasks: Vec<TaskSummary>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct TaskSummary {
    pub task_id: String,
    pub status: String,
    pub created_at: String,
    pub execution_time: f64,
    pub prompt_preview: String,
}

/// API 客户端错误
#[derive(Debug, Serialize)]
pub struct ApiError {
    pub message: String,
    pub code: u16,
}

/// 应用全局状态
pub struct AppState {
    pub config: Mutex<ServerConfig>,
    pub client: Mutex<Option<reqwest::Client>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            config: Mutex::new(ServerConfig::default()),
            client: Mutex::new(None),
        }
    }

    pub fn ensure_client(&self) -> Result<reqwest::Client, String> {
        let mut client = self.client.lock().map_err(|e| e.to_string())?;
        if client.is_none() {
            *client = Some(reqwest::Client::new());
        }
        Ok(client.get_or_insert_with(reqwest::Client::new).clone())
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}
