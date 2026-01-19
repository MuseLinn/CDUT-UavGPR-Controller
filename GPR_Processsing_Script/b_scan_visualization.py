import os
import numpy as np
from numpy.linalg import eig, inv
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.font_manager as fm
from matplotlib.backends.backend_qtagg import FigureCanvasQT
from matplotlib.animation import FuncAnimation

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


# 添加对tempfile和shutil模块的支持
import tempfile
import shutil


class BScan:
    """B扫描数据类，支持链式调用处理方法"""
    
    def __init__(self, data):
        """
        初始化BScan对象
        
        参数:
        data: B-scan数据矩阵 (numpy array)
        """
        self.data = data.copy()
    
    def copy(self):
        """
        创建当前BScan对象的副本
        
        返回:
        BScan对象的副本
        """
        return BScan(self.data)
    
    def apply_agc(self, agc_type='mean', agc_window=None, **kwargs):
        """
        对B-scan数据应用自动增益控制（AGC）
        
        参数:
        agc_type: AGC类型 ('mean', 'median', 'rms')
        agc_window: 窗口大小（用于局部AGC计算）
        kwargs: 其他参数
            min_gain: 最小增益（默认0.1）
            max_gain: 最大增益（默认10.0）
        
        返回:
        self: 返回对象本身以支持链式调用
        """
        # 创建B-scan数据的副本，避免修改原始数据
        b_scan_processed = np.copy(self.data)
        
        # 获取增益限制参数
        min_gain = kwargs.get('min_gain', 0.1)
        max_gain = kwargs.get('max_gain', 10.0)
        
        if agc_type == 'mean':
            # 基于平均值的AGC
            if agc_window:
                # 局部AGC
                gains = np.zeros_like(b_scan_processed)
                for i in range(b_scan_processed.shape[1]):
                    for j in range(0, b_scan_processed.shape[0], agc_window):
                        end_j = min(j + agc_window, b_scan_processed.shape[0])
                        local_mean = np.mean(np.abs(b_scan_processed[j:end_j, i]))
                        gains[j:end_j, i] = 1.0 / np.clip(local_mean, min_gain, max_gain)
            else:
                # 全局AGC
                trace_means = np.mean(np.abs(b_scan_processed), axis=0, keepdims=True)
                gains = 1.0 / np.clip(trace_means, min_gain, max_gain)
                
        elif agc_type == 'median':
            # 基于中位数的AGC
            if agc_window:
                # 局部AGC
                gains = np.zeros_like(b_scan_processed)
                for i in range(b_scan_processed.shape[1]):
                    for j in range(0, b_scan_processed.shape[0], agc_window):
                        end_j = min(j + agc_window, b_scan_processed.shape[0])
                        local_median = np.median(np.abs(b_scan_processed[j:end_j, i]))
                        gains[j:end_j, i] = 1.0 / np.clip(local_median, min_gain, max_gain)
            else:
                # 全局AGC
                trace_medians = np.median(np.abs(b_scan_processed), axis=0, keepdims=True)
                gains = 1.0 / np.clip(trace_medians, min_gain, max_gain)
                
        elif agc_type == 'rms':
            # 基于均方根的AGC
            if agc_window:
                # 局部AGC
                gains = np.zeros_like(b_scan_processed)
                for i in range(b_scan_processed.shape[1]):
                    for j in range(0, b_scan_processed.shape[0], agc_window):
                        end_j = min(j + agc_window, b_scan_processed.shape[0])
                        local_rms = np.sqrt(np.mean(b_scan_processed[j:end_j, i]**2))
                        gains[j:end_j, i] = 1.0 / np.clip(local_rms, min_gain, max_gain)
            else:
                # 全局AGC
                trace_rms = np.sqrt(np.mean(b_scan_processed**2, axis=0, keepdims=True))
                gains = 1.0 / np.clip(trace_rms, min_gain, max_gain)
        else:
            print(f"未知的AGC类型: {agc_type}，返回原始数据")
            return self
        
        # 应用增益
        self.data = b_scan_processed * gains
        
        print(f"AGC处理完成: 类型={agc_type}, 窗口大小={agc_window}")
        return self
    
    def suppress_background(self, method='mean', **kwargs):
        """
        对B-scan数据进行背景抑制
        
        参数:
        method: 背景抑制方法 ('mean', 'median', 'first_trace', 'direct_wave')
        kwargs: 其他参数
            strength: 抑制强度（已移除自适应方法）
            window_size: 窗口大小（用于直达波识别）
        
        返回:
        self: 返回对象本身以支持链式调用
        """
        # 创建B-scan数据的副本，避免修改原始数据
        b_scan_processed = np.copy(self.data)
        
        if method == 'mean':
            # 使用平均背景抑制：减去每行的平均值
            background = np.mean(b_scan_processed, axis=1, keepdims=True)
            b_scan_processed = b_scan_processed - background
        elif method == 'median':
            # 使用中位数背景抑制：减去每行的中位数
            background = np.median(b_scan_processed, axis=1, keepdims=True)
            b_scan_processed = b_scan_processed - background
        elif method == 'first_trace':
            # 使用第一条迹线作为背景进行抑制
            background = b_scan_processed[:, 0:1]  # 保持维度
            b_scan_processed = b_scan_processed - background
        elif method == 'direct_wave':
            # 使用更有效的直达波抑制方法
            # 计算每个道的平均值作为该道的直流分量
            dc_component = np.mean(b_scan_processed, axis=0, keepdims=True)
            # 估计直达波（假设直达波在所有道中基本一致）
            direct_wave = np.median(b_scan_processed, axis=1, keepdims=True)
            # 从数据中减去直达波和直流分量
            b_scan_processed = b_scan_processed - direct_wave - dc_component
        else:
            print(f"未知的背景抑制方法: {method}，返回原始数据")
            
        self.data = b_scan_processed
        return self
    
    def stack_b_scan(self, stack_num=1):
        """
        将相邻的几道A-scan叠加为一道以提高信噪比
        
        参数:
        stack_num: 叠加数量，即将多少道相邻的A-scan合并为一道（默认为1，即不叠加）
        
        返回:
        self: 返回对象本身以支持链式调用
        """
        if stack_num <= 1:
            # 如果stack_num<=1，则不进行叠加
            return self
        
        b_scan = self.data
        num_points, num_scans = b_scan.shape
        # 计算叠加后的道数
        stacked_num_scans = num_scans // stack_num
        
        if stacked_num_scans == 0:
            raise ValueError("叠加数量大于总道数，无法进行叠加")
        
        # 初始化叠加后的B-scan矩阵
        stacked_b_scan = np.zeros((num_points, stacked_num_scans))
        
        # 对每一道叠加后的数据进行计算
        for i in range(stacked_num_scans):
            start_idx = i * stack_num
            end_idx = min((i + 1) * stack_num, num_scans)
            # 使用平均值进行叠加
            stacked_b_scan[:, i] = np.mean(b_scan[:, start_idx:end_idx], axis=1)
        
        print(f"完成数据叠加：原始道数={num_scans}，叠加数量={stack_num}，叠加后道数={stacked_num_scans}")
        self.data = stacked_b_scan
        return self
    
    def apply_bandpass_filter(self, low_freq, high_freq, sampling_rate):
        """
        对B-scan数据应用带通滤波器
        
        参数:
        low_freq: 低频截止频率 (MHz)
        high_freq: 高频截止频率 (MHz)
        sampling_rate: 采样率 (MHz)
        
        返回:
        self: 返回对象本身以支持链式调用
        """
        try:
            from scipy.signal import butter, sosfiltfilt
        except ImportError:
            print("警告: scipy未安装，无法应用带通滤波器")
            return self
        
        b_scan = self.data
        # 计算奈奎斯特频率
        nyquist = 0.5 * sampling_rate
        
        # 归一化频率
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        # 设计带通滤波器 (4阶)
        sos = butter(4, [low, high], btype='band', output='sos')
        
        # 对每一道应用滤波器
        filtered_b_scan = np.zeros_like(b_scan)
        for i in range(b_scan.shape[1]):
            filtered_b_scan[:, i] = sosfiltfilt(sos, b_scan[:, i])
        
        print(f"应用带通滤波器: {low_freq}MHz - {high_freq}MHz, 采样率: {sampling_rate}MHz")
        self.data = filtered_b_scan
        return self
    
    def get_data(self):
        """
        获取B-scan数据
        
        返回:
        B-scan数据的numpy数组副本
        """
        return self.data.copy()
    
    def plot(self, output_file=None, time_start=0, time_end=None, cmap_type='custom_gray'):
        """
        绘制B-scan热力图
        
        参数:
        output_file: 输出文件路径（可选）
        time_start: 时间起始点（默认为0）
        time_end: 时间结束点（默认为根据数据点数自动计算）
        cmap_type: 颜色映射类型 ('gray', 'viridis', 'plasma', 'jet', 'custom_gray')
        
        返回:
        self: 返回对象本身以支持链式调用
        """
        b_scan = self.data
        # 时间范围：根据实际参数计算
        num_points = b_scan.shape[0]
        
        # 如果未指定结束时间，则根据数据点数自动计算（假设每个点间隔2ns）
        if time_end is None:
            time_step = 2  # 默认每个点间隔2ns
            time_end = time_start + (num_points - 1) * time_step
        
        # 根据起始时间和结束时间计算时间轴
        time_range = np.linspace(time_start, time_end, num_points)
        
        # 打印调试信息
        print(f"调试信息:")
        print(f"  数据点数: {num_points}")
        print(f"  时间范围: {time_start} - {time_end} ns")
        print(f"  时间间隔: {time_range[1] - time_range[0] if len(time_range) > 1 else 0} ns")
        
        # 道数范围
        scan_range = np.arange(1, b_scan.shape[1] + 1)
        
        # 设置颜色映射
        if cmap_type == 'custom_gray':
            # 创建自定义颜色映射（黑白灰度）
            colors = [(0, 0, 0), (1, 1, 1)]  # 从黑到白
            cmap = LinearSegmentedColormap.from_list('custom_gray', colors, N=256)
        else:
            # 使用matplotlib内置颜色映射
            cmap = cmap_type
        
        # 绘制热力图
        plt.figure(figsize=(12, 8))
        im = plt.imshow(b_scan, aspect='auto', cmap=cmap, 
                        extent=[scan_range[0], scan_range[-1], time_range[-1], time_range[0]])
        
        # 添加颜色条
        cbar = plt.colorbar(im)
        cbar.set_label('S21 Real(U)')
        
        # 设置标签和标题
        plt.xlabel('道数')
        plt.ylabel('时延 (ns)')
        
        # 根据输出文件名设置图像标题
        if output_file:
            # 从文件名生成标题（去掉扩展名）
            title = os.path.splitext(os.path.basename(output_file))[0]
            # 将下划线替换为空格，使标题更易读
            # title = title.replace('_', ' ')
            plt.title(title)
        else:
            plt.title('B-scan 灰度图')
        
        plt.tight_layout()
        
        # 保存图像或显示
        if output_file:
            plt.savefig(output_file, dpi=300)
            print(f"图像已保存至 {output_file}")
            # plt.show()
        else:
            plt.show()
            
        return self
    
    def animate_a_scan(self, output_gif="a_scan_animation.gif", time_per_scan=200, fps=10, max_frames=100):
        """
        创建A-scan动态图像并保存为GIF
        
        参数:
        output_gif: 输出GIF文件路径
        time_per_scan: 每个A-scan的时间长度（纳秒）
        fps: 帧率（每秒帧数）
        max_frames: 最大帧数，用于控制GIF大小
        
        返回:
        self: 返回对象本身以支持链式调用
        """
        try:
            import imageio.v2 as imageio
        except ImportError:
            print("警告: 需要安装imageio库才能生成GIF动画: pip install imageio")
            return self
        
        b_scan = self.data
        
        # 获取A-scan的数量
        num_scans = b_scan.shape[1]
        
        # 创建时间轴（假定每个A-scan有固定的时间长度）
        time_axis = np.linspace(0, time_per_scan, b_scan.shape[0])
        
        # 创建临时目录来存储帧
        temp_dir = tempfile.mkdtemp()
        
        try:
            frame_files = []
            
            # 确定帧间隔以控制总帧数
            frame_step = max(1, num_scans // max_frames)
            
            print(f"生成动画帧，共 {num_scans//frame_step} 帧...")
            
            # 创建固定的图形和轴
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # 初始化线条
            line, = ax.plot([], [], lw=2)
            
            # 设置轴限制
            ax.set_xlim(time_axis[0], time_axis[-1])
            ax.set_ylim(np.min(b_scan), np.max(b_scan))
            
            # 设置标签
            ax.set_xlabel('时间 (ns)')
            ax.set_ylabel('S21 Real(U)')
            
            # 为每个选定的A-scan生成图像
            for i in range(0, num_scans, frame_step):
                # 更新数据
                line.set_data(time_axis, b_scan[:, i])
                ax.set_title(f'A-scan #{i+1} 动态变化')
                
                # 保存帧到临时文件
                frame_file = os.path.join(temp_dir, f'frame_{i:04d}.png')
                plt.savefig(frame_file, dpi=100, bbox_inches='tight')
                frame_files.append(frame_file)
                
                # 显示进度
                if (i // frame_step + 1) % 10 == 0:
                    print(f"已生成 {i // frame_step + 1} 帧")
            
            plt.close(fig)
            
            # 从帧创建GIF
            if frame_files:
                with imageio.get_writer(output_gif, mode='I', fps=fps) as writer:
                    for frame_file in frame_files:
                        image = imageio.imread(frame_file)
                        writer.append_data(image)
                
                print(f"GIF动画已保存至 {output_gif}")
            else:
                print("未能生成GIF动画")
                
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir)
        
        return self


def read_a_scan(csv_file):
    """读取单个CSV文件中的A-scan数据"""
    # 跳过前7行表头，读取数据
    data = np.genfromtxt(csv_file, delimiter=',', skip_header=7, skip_footer=1)
    # 返回S21 Real(U)值（第二列）
    return data[:, 1]

def read_full_a_scan(csv_file):
    """读取单个CSV文件中的完整A-scan数据，包括时间轴"""
    # 跳过前7行表头，读取数据
    data = np.genfromtxt(csv_file, delimiter=',', skip_header=7, skip_footer=1)
    # 返回完整数据（时间轴和S21 Real(U)值）
    return data[:, 0], data[:, 1]  # 第一列是时间，第二列是S21 Real(U)


def generate_b_scan(folder_path):
    """从文件夹中的所有CSV文件生成B-scan数据"""
    # 获取文件夹中所有CSV文件
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    csv_files.sort()  # 按文件名排序
    
    if not csv_files:
        raise ValueError("文件夹中没有找到CSV文件")
    
    # 读取第一个文件获取A-scan长度
    first_file = os.path.join(folder_path, csv_files[0])
    first_scan = read_a_scan(first_file)
    num_points = len(first_scan)
    num_scans = len(csv_files)

    # 初始化B-scan矩阵
    b_scan = np.zeros((num_points, num_scans))
    
    # 读取每个A-scan并填充到B-scan矩阵
    for i, csv_file in enumerate(csv_files):
        file_path = os.path.join(folder_path, csv_file)
        b_scan[:, i] = read_a_scan(file_path)
        # 显示进度
        if (i + 1) % 10 == 0 or i + 1 == num_scans:
            print(f"已处理 {i + 1}/{num_scans} 个文件")
    
    return BScan(b_scan)


if __name__ == "__main__":
    # 替换为你的CSV文件所在文件夹路径
    folder_path = r"C:\Users\Di Jianhao\Desktop\frp_0.52.3_windows_amd64\out_s21" # 示例路径
    
    try:
        # 生成B-scan数据
        print("正在处理CSV文件...")
        b_scan_data = generate_b_scan(folder_path)

        test_data = b_scan_data.copy().suppress_background(method='median')
        plt.figure(figsize=(10, 6))
        plt.imshow(test_data.data, cmap='gray', aspect='auto')
        plt.xlabel('A-Scan Unit')
        plt.ylabel('Time (ns)')
        plt.title('B-Scan Grayscale Plot')
        plt.colorbar()
        plt.show()

        # TCR目标杂波比 20lg_10((1/N_T * \sum (p,q)属于T |X(p,q)|^2)/(1/N_C * \sum (p,q)属于C |X(p,q)|^2))
        import numpy as np


        def calculate_TCR(b_scan):
            """
            计算探地雷达（GPR）B-Scan数据的目标杂波比（TCR）
            计算公式参考文档：TCR(dB) = 20*log10(目标区域平均功率 / 杂波区域平均功率)

            参数：
            b_scan: np.array，形状为(501, 2383)的B-Scan矩阵，行对应0-700ns，列对应2383个A-Scan

            返回：
            tcr_db: float，TCR值（单位：dB）
            """
            # 1. 定义杂波区域（600-700ns）：根据行索引确定范围（501行对应0-700ns，行索引与时间的映射为：行索引 = (时间ns / 700ns) * 500，取整）
            # 600ns对应的行索引：(600 / 700) * 500 ≈ 428.57 → 取429；700ns对应行索引500（因0ns对应行0）
            clutter_row_start = 429  # 600ns对应的起始行索引
            clutter_row_end = 500  # 700ns对应的结束行索引（含）
            # 提取杂波区域数据：所有列（2383个A-Scan）的杂波行
            clutter_region = b_scan[clutter_row_start:clutter_row_end + 1, :]

            # 2. 定义目标区域：需根据实际目标位置调整（此处为示例，假设目标位于100-300ns，可根据实际数据修改行索引范围）
            # 100ns对应行索引：(100 / 700)*500 ≈ 71.42 → 71；300ns对应行索引：(300/700)*500≈214.28→214
            target_row_start = 71  # 目标起始行索引（示例，需替换为实际目标起始时间对应的行）
            target_row_end = 214  # 目标结束行索引（示例，需替换为实际目标结束时间对应的行）
            # 提取目标区域数据：所有列（2383个A-Scan）的目标行（若目标仅在部分列，可进一步限制列范围，如[:, 500:1500]）
            target_region = b_scan[target_row_start:target_row_end + 1, :]

            # 3. 计算目标区域平均功率（像素强度平方的均值）
            # 文档定义：目标区域平均功率 = (1/N_T) * Σ|X(p,q)|²，其中N_T为目标区域像素数
            target_power = np.mean(np.square(np.abs(target_region)))
            N_T = target_region.size  # 目标区域总像素数（行数×列数）
            # 验证：target_power也可通过 (np.sum(np.square(np.abs(target_region))) / N_T) 计算，结果一致

            # 4. 计算杂波区域平均功率
            # 文档定义：杂波区域平均功率 = (1/N_C) * Σ|X(p,q)|²，其中N_C为杂波区域像素数
            clutter_power = np.mean(np.square(np.abs(clutter_region)))
            N_C = clutter_region.size  # 杂波区域总像素数

            # 5. 计算TCR（避免除以零，添加微小值）
            epsilon = 1e-10  # 防止杂波功率为0导致计算错误
            tcr_db = 20 * np.log10((target_power + epsilon) / (clutter_power + epsilon))

            return tcr_db


        # ------------------- 调用示例 -------------------
        # 假设你的B-Scan数据已通过b_scan = np.array(s21_real).reshape(501, -1)生成
        tcr_result = calculate_TCR(b_scan_data.copy().data)
        print(f"TCR值：{tcr_result:.2f} dB")


        # TODO: CHECK the algorithm after our project finished
        # 1. time-index conversion
        def time_to_point(time, start_time, end_time, ascan_points):
            """
            Calculate the mapping relationship between "time and row index"
            Time unit: ns
            """
            time_range = end_time - start_time
            point_converted = int(time / time_range * ascan_points)
            print(f"time: {time}, mapped to point: {point_converted}")
            return point_converted


        # 2. slice to get the noise background(50-380ns)
        noise_data = test_data.data[time_to_point(400, 0, 700, 501):time_to_point(500, 0, 700, 501)]
        noise_data.std()
        print(f"noise std: {noise_data.std()}")
        # get the target area data(signal + noise)
        target_data = test_data.data

        # 3. calculate the average power ratio of background noise
        noise_mean = noise_data.mean()
        print(f"noise mean: {noise_mean}")
        # calculate the average power ratio of target area
        target_mean = target_data.mean()
        print(f"target mean: {target_mean}")

        # 4. calculate the SNR
        SNR_linear = target_mean / noise_mean
        SNR_dB = 10 * np.log10(SNR_linear)
        print(f"SNR_linear: {SNR_linear}, SNR_dB: {SNR_dB}")

        # 取其中一道A-Scan的一段时间作为噪声信号，完整A-Scan数据作为信号，计算这个信噪比
        a_scan_data = b_scan_data.data[:, 1300]
        a_scan_noise = a_scan_data[time_to_point(400, 0, 700, 501):time_to_point(500, 0, 700, 501)]
        a_scan_signal = a_scan_data
        SNR_linear = a_scan_signal.mean() / a_scan_noise.mean()
        SNR_dB = 10 * np.log10(SNR_linear)
        print(f"A-Scan SNR_linear: {SNR_linear}, SNR_dB: {SNR_dB}")

        import numpy as np


        def time_to_index(t_ns, total_ns=700.0, n_samples=501):
            dt = total_ns / (n_samples - 1)
            return int(np.floor(t_ns / dt))


        # 假设 bscan 是一个 numpy 数组，shape = (n_traces, n_samples)
        # 如果数据是 (time, traces) 转置一下： bscan = bscan.T
        def compute_snr_global_windows(bscan):
            n_traces, n_samples = bscan.shape
            i_100 = time_to_index(100.0, total_ns=700.0, n_samples=n_samples)  # 71
            # signal: 0..i_100, noise: i_100+1 .. end
            signal = bscan[:, :i_100 + 1]  # shape (n_traces, n_sig_samples)
            noise = bscan[:, i_100 + 1:]  # shape (n_traces, n_noise_samples)

            # per-trace SNR (rms-based)
            rms_signal = np.sqrt(np.mean(signal ** 2, axis=1))
            rms_noise = np.sqrt(np.mean(noise ** 2, axis=1)) + 1e-12
            snr_lin = rms_signal / rms_noise
            snr_db_per_trace = 20.0 * np.log10(snr_lin)

            # overall SNR (aggregate)
            rms_signal_all = np.sqrt(np.mean(signal ** 2))
            rms_noise_all = np.sqrt(np.mean(noise ** 2)) + 1e-12
            snr_db_overall = 20.0 * np.log10(rms_signal_all / rms_noise_all)

            return {
                'snr_db_per_trace': snr_db_per_trace,
                'snr_db_overall': snr_db_overall,
                'i_100': i_100
            }

        data= b_scan_data.data.T
        print(data.shape)
        compute_snr_global_windows(data)
        print(compute_snr_global_windows(data))
        print(" Done.")

        # 示例1: 使用传统方式处理数据
        # print("=== 使用传统方式处理数据 ===")
        # 可选：对B-scan数据进行叠加以提高信噪比
        # 将每3道相邻的A-scan叠加为一道
        # b_scan_stacked = b_scan_data.copy().stack_b_scan(stack_num=3)

        # 可选：应用带通滤波器以增强有效信号
        # 根据GPR参数设置滤波器，例如20MHz-170MHz数据，保留主要信号频段
        # b_scan_filtered = apply_bandpass_filter(b_scan_stacked, low_freq=30, high_freq=150, sampling_rate=200)

        # 绘制并保存图像
        # output_image = "b_scan_visualization.png"
        # # 可以自定义时间范围，例如：
        # b_scan_stacked.plot(output_image, time_start=0, time_end=700)  # 使用内置灰度映射
        # 或使用默认参数自动计算时间范围
        # plot_b_scan(b_scan_data, output_image)

        # 对B-scan数据进行背景抑制
        # b_scan_processed = b_scan_data.copy().suppress_background(method='mean')
        # b_scan_processed.plot("b_scan_visualization_mean.png", time_start=0, time_end=700)
        # b_scan_processed = b_scan_stacked.copy().suppress_background(method='mean')
        # b_scan_processed.plot("b_scan_visualization_mean_stacked.png", time_start=0, time_end=700)
        # b_scan_processed = b_scan_stacked.copy().suppress_background(method='median')
        # b_scan_processed.plot("b_scan_visualization_median.png", time_start=0, time_end=700)
        # b_scan_processed = b_scan_stacked.copy().suppress_background(method='first_trace')
        # b_scan_processed.plot("b_scan_visualization_first_trace.png", time_start=0, time_end=700)
        # b_scan_processed = b_scan_stacked.copy().suppress_background(method='direct_wave')
        # b_scan_processed.plot("b_scan_visualization_direct_wave.png", time_start=0, time_end=700)
        
        # # 示例2: 使用链式调用处理数据
        # print("\n=== 使用链式调用处理数据 ===")
        # # 链式调用示例：叠加 -> 背景抑制 -> AGC处理
        # b_scan_result = b_scan_data.copy().stack_b_scan(stack_num=3).suppress_background(method='mean').apply_agc(agc_type='mean')
        # b_scan_result.plot("b_scan_chain_processed.png", time_start=0, time_end=700)
        #
        # # 另一个链式调用示例：叠加 -> 背景抑制(不同方法) -> AGC处理(不同参数)
        # b_scan_result2 = b_scan_data.copy().stack_b_scan(stack_num=3).suppress_background(method='direct_wave').apply_agc(agc_type='rms', agc_window=50)
        # b_scan_result2.plot("b_scan_chain_processed2.png", time_start=0, time_end=700)
        #
        # # 示例3: 生成A-scan动态变化GIF动画
        # print("\n=== 生成A-scan动态变化GIF动画 ===")
        # b_scan_data.animate_a_scan("a_scan_animation.gif", fps=20, max_frames=120)

        print("处理完成！")
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
