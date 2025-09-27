"""
Production System Module - Sistema completo para produção.

Funcionalidades:
- Logging estruturado e detalhado
- Monitoramento em tempo real
- Health checks e métricas
- Error handling robusto
- Sistema de alertas
"""

import logging
import logging.handlers
import json
import time
import threading
import queue
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
import traceback
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from .performance_optimization import PerformanceProfiler, MemoryOptimizer
from ..search_algorithms.base_search import SearchQuery, SearchResult


@dataclass
class HealthStatus:
    """Status de saúde do sistema."""
    
    service_name: str
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    response_time_ms: float
    error_count: int
    warning_count: int
    details: Dict[str, Any]


@dataclass
class Alert:
    """Alerta do sistema."""
    
    alert_id: str
    severity: str  # critical, warning, info
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = None


class StructuredLogger:
    """
    Sistema de logging estruturado.
    
    Cria logs JSON com contexto rico para análise e monitoramento.
    """
    
    def __init__(self, 
                 name: str,
                 log_file: str = "renamepdfepub.log",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 log_level: str = "INFO"):
        """
        Inicializa logger estruturado.
        
        Args:
            name: Nome do logger
            log_file: Arquivo de log
            max_file_size: Tamanho máximo do arquivo
            backup_count: Número de backups
            log_level: Nível de log
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        # Formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Context storage
        self.context = threading.local()
    
    def set_context(self, **kwargs):
        """Define contexto para logs subsequentes."""
        if not hasattr(self.context, 'data'):
            self.context.data = {}
        
        self.context.data.update(kwargs)
    
    def clear_context(self):
        """Limpa contexto atual."""
        if hasattr(self.context, 'data'):
            self.context.data.clear()
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Formata mensagem com contexto."""
        log_data = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'thread_id': threading.get_ident(),
        }
        
        # Add context
        if hasattr(self.context, 'data'):
            log_data.update(self.context.data)
        
        # Add additional data
        log_data.update(kwargs)
        
        return json.dumps(log_data, default=str, ensure_ascii=False)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message."""
        if error:
            kwargs.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc()
            })
        
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, error: Exception = None, **kwargs):
        """Log critical message."""
        if error:
            kwargs.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc()
            })
        
        self.logger.critical(self._format_message(message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message, **kwargs))


class SystemMonitor:
    """
    Monitor de sistema em tempo real.
    
    Monitora performance, erros e saúde geral do sistema.
    """
    
    def __init__(self, 
                 logger: StructuredLogger,
                 profiler: PerformanceProfiler,
                 memory_optimizer: MemoryOptimizer,
                 check_interval: int = 30):
        """
        Inicializa monitor.
        
        Args:
            logger: Logger estruturado
            profiler: Profiler de performance
            memory_optimizer: Otimizador de memória
            check_interval: Intervalo de checagem em segundos
        """
        self.logger = logger
        self.profiler = profiler
        self.memory_optimizer = memory_optimizer
        self.check_interval = check_interval
        
        # Health status
        self.health_checks = {}
        self.last_health_check = {}
        
        # Alerts
        self.active_alerts = {}
        self.alert_handlers = []
        
        # Monitoring state
        self.monitoring = True
        self.monitor_thread = None
        
        # Metrics collection
        self.metrics_queue = queue.Queue()
        self.metrics_history = []
        
        # Thresholds
        self.thresholds = {
            'response_time_ms': 5000,  # 5 seconds
            'memory_usage_mb': 500,
            'error_rate_percent': 5.0,
            'cache_hit_rate_min': 0.3
        }
    
    def register_health_check(self, name: str, check_function: Callable[[], Dict[str, Any]]):
        """
        Registra health check.
        
        Args:
            name: Nome do health check
            check_function: Função que retorna status
        """
        self.health_checks[name] = check_function
        self.logger.info("Health check registered", component=name)
    
    def register_alert_handler(self, handler: Callable[[Alert], None]):
        """
        Registra handler de alertas.
        
        Args:
            handler: Função para processar alertas
        """
        self.alert_handlers.append(handler)
        self.logger.info("Alert handler registered")
    
    def start_monitoring(self):
        """Inicia monitoramento."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("System monitoring started", interval=self.check_interval)
    
    def stop_monitoring(self):
        """Para monitoramento."""
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("System monitoring stopped")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Obtém status completo de saúde do sistema."""
        health_data = {}
        overall_status = "healthy"
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = check_func()
                response_time = (time.time() - start_time) * 1000
                
                health_status = HealthStatus(
                    service_name=name,
                    status=result.get('status', 'unknown'),
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    error_count=result.get('error_count', 0),
                    warning_count=result.get('warning_count', 0),
                    details=result.get('details', {})
                )
                
                health_data[name] = asdict(health_status)
                
                # Update overall status
                if health_status.status == 'unhealthy':
                    overall_status = 'unhealthy'
                elif health_status.status == 'degraded' and overall_status != 'unhealthy':
                    overall_status = 'degraded'
                
                self.last_health_check[name] = health_status
                
            except Exception as e:
                self.logger.error(f"Health check failed for {name}", error=e)
                health_data[name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                overall_status = 'unhealthy'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'services': health_data,
            'active_alerts': len(self.active_alerts),
            'system_metrics': self._get_system_metrics()
        }
    
    def create_alert(self, 
                    severity: str,
                    component: str,
                    message: str,
                    metadata: Dict[str, Any] = None) -> str:
        """
        Cria novo alerta.
        
        Args:
            severity: Severidade do alerta
            component: Componente afetado
            message: Mensagem do alerta
            metadata: Metadados adicionais
            
        Returns:
            str: ID do alerta
        """
        alert_id = f"{component}_{int(time.time())}"
        
        alert = Alert(
            alert_id=alert_id,
            severity=severity,
            component=component,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.active_alerts[alert_id] = alert
        
        # Log alert
        self.logger.warning(
            f"Alert created: {message}",
            alert_id=alert_id,
            severity=severity,
            component=component,
            metadata=metadata
        )
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error("Alert handler failed", error=e)
        
        return alert_id
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve alerta.
        
        Args:
            alert_id: ID do alerta
            
        Returns:
            bool: True se resolvido
        """
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            self.logger.info("Alert resolved", alert_id=alert_id)
            return True
        
        return False
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Obtém resumo de métricas.
        
        Args:
            hours: Horas para incluir no resumo
            
        Returns:
            Dict[str, Any]: Resumo das métricas
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
        
        if not recent_metrics:
            return {'error': 'no_recent_metrics'}
        
        # Calculate aggregations
        response_times = [m['response_time_ms'] for m in recent_metrics if 'response_time_ms' in m]
        error_counts = [m['error_count'] for m in recent_metrics if 'error_count' in m]
        
        return {
            'period_hours': hours,
            'total_metrics': len(recent_metrics),
            'average_response_time_ms': sum(response_times) / len(response_times) if response_times else 0,
            'total_errors': sum(error_counts),
            'peak_memory_mb': max(m.get('memory_mb', 0) for m in recent_metrics),
            'alerts_created': len([a for a in recent_metrics if 'alert_created' in a]),
            'system_availability': self._calculate_availability(recent_metrics)
        }
    
    def _monitoring_loop(self):
        """Loop principal de monitoramento."""
        while self.monitoring:
            try:
                # Run health checks
                health_status = self.get_system_health()
                
                # Check for issues
                self._check_thresholds(health_status)
                
                # Collect metrics
                metrics = self._collect_current_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only recent metrics (last 7 days)
                cutoff_time = datetime.now() - timedelta(days=7)
                self.metrics_history = [
                    m for m in self.metrics_history
                    if datetime.fromisoformat(m['timestamp']) > cutoff_time
                ]
                
                # Memory optimization if needed
                memory_status = self.memory_optimizer.check_memory_usage()
                if memory_status['is_over_limit']:
                    self.logger.warning("Memory usage over limit", **memory_status)
                    optimization_result = self.memory_optimizer.optimize_if_needed()
                    
                    if optimization_result['optimized']:
                        self.logger.info("Memory optimization completed", **optimization_result)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error("Monitoring loop error", error=e)
                time.sleep(self.check_interval)
    
    def _check_thresholds(self, health_status: Dict[str, Any]):
        """Verifica thresholds e cria alertas se necessário."""
        for service_name, service_data in health_status.get('services', {}).items():
            # Check response time
            response_time = service_data.get('response_time_ms', 0)
            if response_time > self.thresholds['response_time_ms']:
                self.create_alert(
                    'warning',
                    service_name,
                    f"High response time: {response_time:.1f}ms",
                    {'threshold': self.thresholds['response_time_ms'], 'actual': response_time}
                )
            
            # Check error count
            error_count = service_data.get('error_count', 0)
            if error_count > 0:
                self.create_alert(
                    'warning' if error_count < 10 else 'critical',
                    service_name,
                    f"Errors detected: {error_count}",
                    {'error_count': error_count}
                )
        
        # Check system metrics
        system_metrics = health_status.get('system_metrics', {})
        
        memory_usage = system_metrics.get('memory_mb', 0)
        if memory_usage > self.thresholds['memory_usage_mb']:
            self.create_alert(
                'warning',
                'system',
                f"High memory usage: {memory_usage:.1f}MB",
                {'threshold': self.thresholds['memory_usage_mb'], 'actual': memory_usage}
            )
    
    def _collect_current_metrics(self) -> Dict[str, Any]:
        """Coleta métricas atuais."""
        performance_report = self.profiler.get_performance_report()
        memory_status = self.memory_optimizer.check_memory_usage()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'memory_mb': memory_status['current_mb'],
            'active_operations': performance_report.get('active_operations', 0),
            'recent_operations': len(performance_report.get('recent_operations', [])),
            'system_cpu': performance_report.get('system_info', {}).get('cpu_percent', 0),
            'alert_count': len(self.active_alerts)
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Obtém métricas do sistema."""
        performance_report = self.profiler.get_performance_report()
        memory_status = self.memory_optimizer.check_memory_usage()
        
        return {
            'memory_mb': memory_status['current_mb'],
            'memory_percentage': memory_status['percentage'],
            'active_operations': performance_report.get('active_operations', 0),
            'average_operation_time': performance_report.get('metrics', {}).average_execution_time,
            'total_operations': getattr(performance_report.get('metrics', {}), '_operation_count', 0)
        }
    
    def _calculate_availability(self, metrics: List[Dict[str, Any]]) -> float:
        """Calcula disponibilidade do sistema."""
        if not metrics:
            return 0.0
        
        healthy_periods = sum(1 for m in metrics if m.get('status') != 'unhealthy')
        return healthy_periods / len(metrics)


class AlertNotifier:
    """
    Sistema de notificação de alertas.
    
    Envia alertas por diferentes canais (email, webhook, etc.).
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa notificador.
        
        Args:
            config: Configuração de notificação
        """
        self.config = config
        self.email_config = config.get('email', {})
        self.webhook_config = config.get('webhook', {})
        
        self.logger = StructuredLogger('AlertNotifier')
    
    def send_alert(self, alert: Alert):
        """
        Envia alerta por todos os canais configurados.
        
        Args:
            alert: Alerta para enviar
        """
        if self.email_config.get('enabled', False):
            self._send_email_alert(alert)
        
        if self.webhook_config.get('enabled', False):
            self._send_webhook_alert(alert)
        
        self.logger.info(
            "Alert notification sent",
            alert_id=alert.alert_id,
            severity=alert.severity,
            component=alert.component
        )
    
    def _send_email_alert(self, alert: Alert):
        """Envia alerta por email."""
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            recipients = self.email_config.get('recipients', [])
            
            if not all([smtp_server, username, password, recipients]):
                return
            
            # Create message
            msg = MimeMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[{alert.severity.upper()}] RenamePDFEPub Alert: {alert.component}"
            
            # Email body
            body = f"""
Alert Details:
- ID: {alert.alert_id}
- Severity: {alert.severity}
- Component: {alert.component}
- Message: {alert.message}
- Timestamp: {alert.timestamp}

Metadata:
{json.dumps(alert.metadata or {}, indent=2)}
            """.strip()
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
        except Exception as e:
            self.logger.error("Failed to send email alert", error=e)
    
    def _send_webhook_alert(self, alert: Alert):
        """Envia alerta por webhook."""
        try:
            import requests
            
            webhook_url = self.webhook_config.get('url')
            if not webhook_url:
                return
            
            payload = {
                'alert_id': alert.alert_id,
                'severity': alert.severity,
                'component': alert.component,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'metadata': alert.metadata
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            response.raise_for_status()
            
        except Exception as e:
            self.logger.error("Failed to send webhook alert", error=e)


class ProductionHealthChecks:
    """
    Health checks específicos para produção.
    
    Implementa checagens de saúde para todos os componentes críticos.
    """
    
    def __init__(self, 
                 search_integration,
                 performance_profiler: PerformanceProfiler,
                 memory_optimizer: MemoryOptimizer):
        """
        Inicializa health checks.
        
        Args:
            search_integration: Integração CLI
            performance_profiler: Profiler de performance
            memory_optimizer: Otimizador de memória
        """
        self.search_integration = search_integration
        self.profiler = performance_profiler
        self.memory_optimizer = memory_optimizer
    
    def check_search_algorithms(self) -> Dict[str, Any]:
        """Verifica saúde dos algoritmos de busca."""
        try:
            # Test basic search functionality
            test_query = "python programming"
            start_time = time.time()
            
            result = self.search_integration.search_intelligent(
                test_query,
                max_results=1,
                use_cache=False
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if 'error' in result:
                return {
                    'status': 'unhealthy',
                    'error_count': 1,
                    'details': {'error': result['error']}
                }
            
            return {
                'status': 'healthy',
                'error_count': 0,
                'warning_count': 0,
                'details': {
                    'response_time_ms': response_time,
                    'results_found': result.get('total_found', 0),
                    'algorithms_available': len(result.get('algorithms_used', []))
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error_count': 1,
                'details': {'error': str(e)}
            }
    
    def check_cache_system(self) -> Dict[str, Any]:
        """Verifica saúde do sistema de cache."""
        try:
            cache_stats = self.search_integration.cache.get_stats()
            
            hit_rate = cache_stats.get('global', {}).get('hit_rate', 0)
            warning_count = 1 if hit_rate < 0.3 else 0
            
            return {
                'status': 'healthy' if hit_rate > 0.1 else 'degraded',
                'error_count': 0,
                'warning_count': warning_count,
                'details': {
                    'hit_rate': hit_rate,
                    'total_requests': cache_stats.get('global', {}).get('total_requests', 0),
                    'cache_size': cache_stats.get('memory', {}).get('current_size', 0)
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error_count': 1,
                'details': {'error': str(e)}
            }
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Verifica uso de memória."""
        try:
            memory_status = self.memory_optimizer.check_memory_usage()
            memory_trends = self.memory_optimizer.get_memory_trends()
            
            if memory_status['is_over_limit']:
                status = 'unhealthy'
                error_count = 1
            elif memory_status['percentage'] > 80:
                status = 'degraded'
                error_count = 0
            else:
                status = 'healthy'
                error_count = 0
            
            return {
                'status': status,
                'error_count': error_count,
                'warning_count': 1 if memory_status['percentage'] > 70 else 0,
                'details': {
                    'current_mb': memory_status['current_mb'],
                    'percentage': memory_status['percentage'],
                    'trend': memory_trends.get('trend', 'unknown'),
                    'peak_mb': memory_trends.get('peak_memory', 0)
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error_count': 1,
                'details': {'error': str(e)}
            }
    
    def check_performance_metrics(self) -> Dict[str, Any]:
        """Verifica métricas de performance."""
        try:
            performance_report = self.profiler.get_performance_report()
            bottlenecks = self.profiler.get_bottlenecks()
            
            warning_count = len(bottlenecks)
            status = 'healthy'
            
            if warning_count > 5:
                status = 'degraded'
            elif warning_count > 10:
                status = 'unhealthy'
            
            avg_time = performance_report.get('metrics', {}).average_execution_time
            
            return {
                'status': status,
                'error_count': 0,
                'warning_count': warning_count,
                'details': {
                    'average_execution_time': avg_time,
                    'active_operations': performance_report.get('active_operations', 0),
                    'bottlenecks_count': len(bottlenecks),
                    'bottlenecks': bottlenecks[:3]  # Top 3 bottlenecks
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error_count': 1,
                'details': {'error': str(e)}
            }