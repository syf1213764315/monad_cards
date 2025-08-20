(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function getGoBtn() {
    // 更严格的Go按钮检测
    return [...document.querySelectorAll("button")]
      .find(b => {
        // 检查按钮是否包含"Go!"文本
        if (!b.innerText.includes("Go!")) return false;
        // 检查按钮是否被禁用
        if (b.disabled) return false;
        // 检查按钮是否可见
        const style = window.getComputedStyle(b);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        // 检查按钮是否在视口内
        const rect = b.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;
        return true;
      });
  }

  function isGameActive() {
    // 检查是否有活跃的楼层（有可点击的门）
    const floors = document.querySelectorAll("div[data-layer-index]");
    if (floors.length === 0) return false;
    
    // 检查是否有任何可点击的门
    const hasClickableDoors = [...document.querySelectorAll("div")].some(div => 
      div.className.includes("cursor-pointer") && 
      div.className.includes("hover:opacity-100")
    );
    
    return hasClickableDoors;
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
    
    // 检查是否所有门都不可点击
    const allDoors = [...document.querySelectorAll("div")].filter(div => 
      div.className.includes("hover:opacity-100")
    );
    const clickableDoors = allDoors.filter(div => 
      div.className.includes("cursor-pointer")
    );
    
    if (allDoors.length > 0 && clickableDoors.length === 0) {
      console.log("🏁 所有门都已不可点击，游戏结束");
      return true;
    }
    
    return false;
  }

  async function continueClimbing() {
    // 直接继续爬楼，不需要点击Go按钮
    console.log("🔄 继续爬楼...");
    
    // 获取当前所有楼层
    let allFloors = [...document.querySelectorAll("div[data-layer-index]")];
    if (allFloors.length === 0) {
      console.log("❌ 没有找到任何楼层");
      return false;
    }
    
    // 找到最高的未点击楼层
    allFloors.sort((a, b) => Number(b.dataset.layerIndex) - Number(a.dataset.layerIndex));
    
    for (const floor of allFloors) {
      const floorIndex = Number(floor.dataset.layerIndex);
      
      // 检查这层是否有可点击的门
      const clickableDoors = [...floor.querySelectorAll("div")].filter(div => 
        div.className.includes("cursor-pointer") && 
        div.className.includes("hover:opacity-100")
      );
      
      if (clickableDoors.length > 0) {
        console.log(`📍 从第 ${floorIndex} 层继续爬楼`);
        return await climbFromFloor(floorIndex);
      }
    }
    
    console.log("❌ 没有找到可点击的楼层");
    return false;
  }

  async function climbFromFloor(startIndex) {
    let currentIndex = startIndex;
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
        currentIndex--;
        continue;
      }
      
      // 检查这层是否已经被点击过（没有可点击的门）
      const hasClickableDoors = [...floor.querySelectorAll("div")].some(div => 
        div.className.includes("cursor-pointer") && 
        div.className.includes("hover:opacity-100")
      );
      
      if (!hasClickableDoors) {
        console.log(`⏭️ 第 ${currentIndex} 层已经点击过，跳过`);
        currentIndex--;
        continue;
      }
      
      // 点击当前层的门
      const success = await clickDoors(floor);
      if (!success) {
        consecutiveFailures++;
        if (consecutiveFailures >= maxFailures) {
          console.error(`❌ 连续 ${maxFailures} 次失败，停止爬楼`);
          break;
        }
        currentIndex--;
        continue;
      }
      
      consecutiveFailures = 0;
      
      // 等待动画完成
      await sleep(500);
      
      // 等待下一层加载
      if (currentIndex > 0) {
        const nextFloor = await waitForNextFloor(currentIndex);
        if (!nextFloor) {
          console.warn(`⚠️ 第 ${currentIndex - 1} 层加载失败`);
          await sleep(1000);
          const retryFloor = document.querySelector(`div[data-layer-index="${currentIndex - 1}"]`);
          if (!retryFloor) {
            break;
          }
        }
      }
      
      currentIndex--;
      
      // 添加随机延迟
      await sleep(300 + Math.random() * 200);
    }
    
    console.log("✅ 本轮爬楼完成");
    return true;
  }

  async function startClimb() {
    // 首先检查是否需要点击Go按钮
    const goBtn = getGoBtn();
    
    if (goBtn) {
      console.log("🚀 找到 Go! 按钮，点击开始");
      goBtn.click();
      
      // 等待游戏开始
      await sleep(1000);
      
      // 获取最高层数
      let allFloors = [...document.querySelectorAll("div[data-layer-index]")];
      if (allFloors.length === 0) {
        console.error("❌ 点击Go后没有找到任何楼层");
        return false;
      }
      
      let currentIndex = Math.max(...allFloors.map(f => Number(f.dataset.layerIndex)));
      console.log(`📊 开始从第 ${currentIndex} 层爬楼`);
      
      return await climbFromFloor(currentIndex);
      
    } else if (isGameActive()) {
      // 游戏已经在进行中，继续爬楼
      console.log("🎮 游戏进行中，继续爬楼");
      return await continueClimbing();
      
    } else {
      // 既没有Go按钮，也没有活跃的游戏
      console.log("⏸️ 游戏未开始或已结束");
      return false;
    }
  }

  // 主循环
  let roundCount = 0;
  let noGameCount = 0;
  const maxNoGameCount = 10;
  
  while (true) {
    try {
      roundCount++;
      console.log(`\n🔄 === 第 ${roundCount} 轮检查 ===`);
      
      const result = await startClimb();
      
      if (result) {
        console.log(`✅ 第 ${roundCount} 轮完成`);
        noGameCount = 0;
      } else {
        noGameCount++;
        console.log(`⚠️ 第 ${roundCount} 轮无操作 (${noGameCount}/${maxNoGameCount})`);
        
        if (noGameCount >= maxNoGameCount) {
          console.log("❌ 连续多次无操作，脚本停止");
          break;
        }
      }
      
      // 等待一段时间再进行下一轮
      await sleep(2000 + Math.random() * 1000);
      
    } catch (e) {
      console.error("❌ 发生错误:", e);
      await sleep(5000);
    }
  }
  
  console.log("🛑 脚本已停止");
})();