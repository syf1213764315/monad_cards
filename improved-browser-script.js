(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function getGoBtn() {
    return [...document.querySelectorAll("button")]
      .find(b => b.innerText.includes("Go!") && !b.disabled);
  }

  async function waitForDoors(floor, timeout = 20000) {
    const start = Date.now();
    
    // 改进的选择器：查找包含cursor-pointer类的门元素
    let doors = [...floor.querySelectorAll("div")].filter(div => 
      div.className.includes("cursor-pointer") && 
      div.className.includes("hover:opacity-100")
    );
    
    while (doors.length === 0) {
      if (Date.now() - start > timeout) {
        console.warn(`⏱️ 第 ${floor.dataset.layerIndex} 层等待超时`);
        return false;
      }
      await sleep(200);
      doors = [...floor.querySelectorAll("div")].filter(div => 
        div.className.includes("cursor-pointer") && 
        div.className.includes("hover:opacity-100")
      );
    }
    
    console.log(`✅ 第 ${floor.dataset.layerIndex} 层找到 ${doors.length} 个可点击的门`);
    return doors;
  }

  async function clickDoors(floor) {
    const doors = await waitForDoors(floor);
    if (!doors || doors.length === 0) {
      console.warn(`⚠️ 第 ${floor.dataset.layerIndex} 层没有找到可点击的门`);
      return false;
    }
    
    // 随机选择一个门点击
    const randomDoor = doors[Math.floor(Math.random() * doors.length)];
    randomDoor.click();
    console.log(`🚪 在第 ${floor.dataset.layerIndex} 层点击了门 (共 ${doors.length} 个可选)`);
    return true;
  }

  async function waitForNextFloor(prevFloorIndex, timeout = 15000) {
    console.log(`⏳ 等待第 ${prevFloorIndex - 1} 层加载...`);
    
    return new Promise(resolve => {
      const start = Date.now();
      const checkInterval = setInterval(() => {
        const nextFloor = document.querySelector(`div[data-layer-index="${prevFloorIndex - 1}"]`);
        
        if (nextFloor) {
          // 确保新楼层已经完全加载（有门可点击）
          const hasClickableDoors = [...nextFloor.querySelectorAll("div")].some(div => 
            div.className.includes("cursor-pointer") && 
            div.className.includes("hover:opacity-100")
          );
          
          if (hasClickableDoors) {
            clearInterval(checkInterval);
            console.log(`✅ 第 ${prevFloorIndex - 1} 层已加载完成`);
            resolve(nextFloor);
            return;
          }
        }
        
        if (Date.now() - start > timeout) {
          clearInterval(checkInterval);
          console.warn(`⏱️ 第 ${prevFloorIndex - 1} 层加载超时`);
          resolve(null);
        }
      }, 300);
    });
  }

  async function checkGameEnd() {
    // 检查是否到达顶层或游戏结束
    const floors = document.querySelectorAll("div[data-layer-index]");
    if (floors.length === 0) return true;
    
    // 检查是否有第0层（通常是顶层）
    const topFloor = document.querySelector('div[data-layer-index="0"]');
    if (topFloor) {
      const hasClickableDoors = [...topFloor.querySelectorAll("div")].some(div => 
        div.className.includes("cursor-pointer") && 
        div.className.includes("hover:opacity-100")
      );
      if (!hasClickableDoors) {
        console.log("🎯 已到达顶层！");
        return true;
      }
    }
    
    return false;
  }

  async function startClimb() {
    // 点击 Go! 按钮
    let goBtn = getGoBtn();
    let waitCount = 0;
    while (!goBtn) {
      if (waitCount++ > 20) {
        console.error("❌ Go! 按钮长时间不可用，停止等待");
        return false;
      }
      console.log("⏳ 等待 Go! 按钮可用...");
      await sleep(500);
      goBtn = getGoBtn();
    }
    
    goBtn.click();
    console.log("🚀 点击 Go!，开始爬楼");
    
    // 等待第一层加载
    await sleep(1000);
    
    // 获取当前最高层数
    let allFloors = [...document.querySelectorAll("div[data-layer-index]")];
    if (allFloors.length === 0) {
      console.error("❌ 没有找到任何楼层");
      return false;
    }
    
    let currentIndex = Math.max(...allFloors.map(f => Number(f.dataset.layerIndex)));
    console.log(`📊 开始从第 ${currentIndex} 层爬楼`);
    
    let consecutiveFailures = 0;
    const maxFailures = 3;
    
    while (currentIndex >= 0) {
      // 检查游戏是否结束
      if (await checkGameEnd()) {
        console.log("🏁 游戏结束");
        break;
      }
      
      const floor = document.querySelector(`div[data-layer-index="${currentIndex}"]`);
      if (!floor) {
        console.warn(`⚠️ 没有找到第 ${currentIndex} 层`);
        break;
      }
      
      // 点击当前层的门
      const success = await clickDoors(floor);
      if (!success) {
        consecutiveFailures++;
        if (consecutiveFailures >= maxFailures) {
          console.error(`❌ 连续 ${maxFailures} 次失败，停止爬楼`);
          break;
        }
        // 尝试继续下一层
        currentIndex--;
        continue;
      }
      
      consecutiveFailures = 0; // 重置失败计数
      
      // 等待一小段时间让动画完成
      await sleep(500);
      
      // 等待下一层加载
      if (currentIndex > 0) {
        const nextFloor = await waitForNextFloor(currentIndex);
        if (!nextFloor) {
          console.warn(`⚠️ 第 ${currentIndex - 1} 层加载失败`);
          // 尝试重新查找
          await sleep(1000);
          const retryFloor = document.querySelector(`div[data-layer-index="${currentIndex - 1}"]`);
          if (!retryFloor) {
            break;
          }
        }
      }
      
      currentIndex--;
      
      // 添加随机延迟，模拟人类行为
      await sleep(300 + Math.random() * 200);
    }
    
    console.log("✅ 本轮爬楼完成");
    return true;
  }

  // 主循环
  let roundCount = 0;
  while (true) {
    try {
      roundCount++;
      console.log(`\n🔄 === 第 ${roundCount} 轮开始 ===`);
      
      const result = await startClimb();
      
      if (result) {
        console.log(`✅ 第 ${roundCount} 轮完成，等待下一轮...`);
      } else {
        console.log(`⚠️ 第 ${roundCount} 轮异常结束，等待重试...`);
      }
      
      // 等待一段时间再开始下一轮
      await sleep(3000 + Math.random() * 2000);
      
    } catch (e) {
      console.error("❌ 发生错误:", e);
      await sleep(5000);
    }
  }
})();