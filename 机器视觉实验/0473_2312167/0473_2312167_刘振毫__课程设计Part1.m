clc; clear; close all;

%分割图像
%Path = "my.jpg";
%fenge(Path)

% 读取图像
files1 = dir('picture/Simple/*.jpg');
files2 = dir('picture/Difficult/*.jpg');
files3 = dir('picture/my/*.jpg');
Path="my.jpg";
myfun(files1,1);
myfun(files2,2);
myfun(files3,3);

function fenge(Path)

step = 1000;  % 分块步长（实际非重叠宽度 = step - r）
r = 200;      % 重叠区域宽度
i = 1;       % 分块索引从1开始

% 读取图像
img = imread(Path);
[~, W, ~] = size(img); 

% 计算总分块数
numBlocks = ceil((W - r) / (step - r)); 
% 预初始化分块存储数组
blocks = cell(1, numBlocks);  % 使用cell数组存储不同大小的块（边缘情况）

% 分块切割循环
while i < numBlocks
    % 计算当前块的列范围
    x_start = max(1, (i-1)*(step - r) + 1);
    x_end = min(W, x_start + step - 1);  % 块宽度可能小于step
    
    blocks{i} = img(:, x_start:x_end, :);
    
    %保存到文件
    imwrite(blocks{i}, sprintf('picture/my/my_%d.jpg', i));
    
    i = i + 1;  % 索引递增
end
blocks{i} = img(:, W-step+1:W, :);
    
    %保存到文件
    imwrite(blocks{i}, sprintf('picture/my/my_%d.jpg', i));
end

function myfun(files,n)
N = numel(files);
images = cell(N,1);
features = cell(N,1);
validPts = cell(N,1);

%读取和特征提取
for i = 1:N
    I = imread(fullfile(files(i).folder, files(i).name));
    images{i} = im2single(I);
    gray = im2single(rgb2gray(I));
    pts = detectSIFTFeatures(gray);
    [features{i}, validPts{i}] = extractFeatures(gray, pts);
end

%拼接顺序按文件名顺序
sequence = 1:N;

%预估变换与重叠宽度

tforms(N) = projective2d(eye(3));
overlaps = zeros(N,1);
for k = 2:N
    i = sequence(k-1);
    j = sequence(k);
    % 特征匹配
    D = pdist2(features{i}, features{j}, 'euclidean');
    [md, idx] = mink(D,2,2);
    sel = (md(:,1) ./ md(:,2)) < 0.7;
    m1 = find(sel);
    if isempty(m1)
        overlaps(k) = 0;
        continue;
    end
    m2 = idx(sel,1);
    pts1 = validPts{i}(m1).Location;
    pts2 = validPts{j}(m2).Location;
    % 估计变换
    tforms(k) = estimateGeometricTransform(pts2, pts1, 'projective', ...
        'MaxNumTrials',2000,'Confidence',99,'MaxDistance',2);
    % 重叠宽度估算
    w1 = size(images{i},2);
    xWarp = transformPointsForward(tforms(k), [1; w1], [1;1]);
    xMin = max(1, ceil(min(xWarp(:,1))));
    xMax = min(w1, floor(max(xWarp(:,1))));
    overlaps(k) = max(0, xMax - xMin + 1);
end

%画布尺寸
totalWidth = size(images{1},2);
for k = 2:N
    totalWidth = totalWidth + size(images{k},2) - overlaps(k);
end
canvasHeight = max(cellfun(@(I) size(I,1), images));
canvas = zeros(canvasHeight, totalWidth, 3, 'single');

%拼接图像
xOffset = 1;
for k = 1:N
    I = images{k};
    [h, w, ~] = size(I);
    if k == 1
        % 放置第一张
        canvas(1:h, xOffset:xOffset+w-1, :) = I;
        xOffset = xOffset + w;
    else
        % 变换
        warped = imwarp(I, imref2d(size(I)), tforms(k));
        mask = rgb2gray(warped) > 0;
        [h2, w2, ~] = size(warped);
        % 计算目标区域
        destX1 = xOffset - overlaps(k);
        destX2 = destX1 + w2 - 1;
        % 裁剪到画布
        destX1c = max(1, destX1);
        destX2c = min(totalWidth, destX2);
        srcX1 = destX1c - destX1 + 1;
        srcLen = destX2c - destX1c + 1;
        srcX2 = srcX1 + srcLen - 1;
        % 裁剪高度
        destY1c = 1;
        destY2c = min(canvasHeight, h2);
      
        % 确认有效范围
        if srcLen > 0 && destY2c >= destY1c
            regionX = destX1c:destX2c;
            regionY = destY1c:destY2c;
            warpedCrop = warped(regionY, srcX1:srcX2, :);
            maskCrop = mask(regionY, srcX1:srcX2);
            mask3 = repmat(maskCrop, [1,1,3]);
            canvas(regionY, regionX, :) = canvas(regionY, regionX, :) .* ~mask3 + warpedCrop .* mask3;
        end
        xOffset = destX2 + 1;
    end
end

% 显示全景
figure; imshow(canvas); title('全景图');

filename = sprintf('全景图_%s.jpg', n);
% 将单精度数据 [0,1] 转换为 uint8 [0,255]
canvas_uint8 = im2uint8(canvas); 
imwrite(canvas_uint8, filename); 
end