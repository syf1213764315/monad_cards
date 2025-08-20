(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function getGoBtn() {
    // 更严格的Go按钮检测
    return [...document.querySelectorAll("button")]
      .find(b => {
        if (!b.innerText.includes("Go!")) return false;
        if (b.disabled) return false;
        const style = window.getComputedStyle(b);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        const rect = b.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;
        return true;
      });
  }

  function isGameActive() {
    // 检查是否有活跃的楼层（有可点击的门）
    const floors = document.querySelectorAll("div[data-layer-index]");
    if (floors.length === 0) return false;
    
    // 更准确的检测：查找真正可点击的门（cursor-pointer 且不是 cursor-not-allowed）
    for (const floor of floors) {
      const doors = floor.querySelectorAll("div");
      for (const door of doors) {
        const classes = door.className;
        // 必须有 cursor-pointer 且没有 cursor-not-allowed
        if (classes.includes("cursor-pointer") && 
            !classes.includes("cursor-not-allowed") &&
            classes.includes("hover:opacity-100")) {
          return true;
        }
      }
    }
    
    return false;
  }

  async function waitForDoors(floor, timeout = 20000) {
    const start = Date.now();
    
    // 修正选择器：排除 cursor-not-allowed 的元素
    let doors = [...floor.querySelectorAll("div")].filter(div => {
      const classes = div.className;
      return classes.includes("cursor-pointer") && 
             !classes.includes("cursor-not-allowed") &&
             classes.includes("hover:opacity-100");
    });
    
    while (doors.length === 0) {
      if (Date.now() - start > timeout) {
        console.warn(`⏱️ 第 ${floor.dataset.layerIndex} 层等待超时`);
        return false;
      }
      await sleep(200);
      doors = [...floor.querySelectorAll("div")].filter(div => {
        const classes = div.className;
        return classes.includes("cursor-pointer") && 
               !classes.includes("cursor-not-allowed") &&
               classes.includes("hover:opacity-100");
      });
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
    
    // 打印更多调试信息
    console.log(`🎯 准备点击第 ${floor.dataset.layerIndex} 层的门`);
    console.log(`   门的class: ${randomDoor.className.substring(0, 100)}...`);
    
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
          // 确保新楼层已经完全加载（有真正可点击的门）
          const hasClickableDoors = [...nextFloor.querySelectorAll("div")].some(div => {
            const classes = div.className;
            return classes.includes("cursor-pointer") && 
                   !classes.includes("cursor-not-allowed") &&
                   classes.includes("hover:opacity-100");
          });
          
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
    if (floors.length === 0) {
      console.log("🏁 没有楼层，游戏结束");
      return true;
    }
    
    // 检查是否所有门都不可点击
    let hasAnyClickableDoor = false;
    for (const floor of floors) {
      const clickableDoors = [...floor.querySelectorAll("div")].filter(div => {
        const classes = div.className;
        return classes.includes("cursor-pointer") && 
               !classes.includes("cursor-not-allowed") &&
               classes.includes("hover:opacity-100");
      });
      if (clickableDoors.length > 0) {
        hasAnyClickableDoor = true;
        break;
      }
    }
    
    if (!hasAnyClickableDoor) {
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
    
    // 找到最高的未点击楼层（从高到低排序）
    allFloors.sort((a, b) => Number(b.dataset.layerIndex) - Number(a.dataset.layerIndex));
    
    for (const floor of allFloors) {
      const floorIndex = Number(floor.dataset.layerIndex);
      
      // 检查这层是否有真正可点击的门
      const clickableDoors = [...floor.querySelectorAll("div")].filter(div => {
        const classes = div.className;
        return classes.includes("cursor-pointer") && 
               !classes.includes("cursor-not-allowed") &&
               classes.includes("hover:opacity-100");
      });
      
      if (clickableDoors.length > 0) {
        console.log(`📍 从第 ${floorIndex} 层继续爬楼（有 ${clickableDoors.length} 个可点击的门）`);
        return await climbFromFloor(floorIndex);
      } else {
        console.log(`⏭️ 第 ${floorIndex} 层已完成或没有可点击的门`);
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
        console.log("🏁 游戏已结束");
        break;
      }
      
      const floor = document.querySelector(`div[data-layer-index="${currentIndex}"]`);
      if (!floor) {
        console.warn(`⚠️ 没有找到第 ${currentIndex} 层`);
        currentIndex--;
        continue;
      }
      
      // 检查这层是否有真正可点击的门
      const hasClickableDoors = [...floor.querySelectorAll("div")].some(div => {
        const classes = div.className;
        return classes.includes("cursor-pointer") && 
               !classes.includes("cursor-not-allowed") &&
               classes.includes("hover:opacity-100");
      });
      
      if (!hasClickableDoors) {
        console.log(`⏭️ 第 ${currentIndex} 层已经点击过或没有可点击的门，跳过`);
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
      await sleep(800);
      
      // 等待下一层加载
      if (currentIndex > 0) {
        const nextFloor = await waitForNextFloor(currentIndex);
        if (!nextFloor) {
          console.warn(`⚠️ 第 ${currentIndex - 1} 层加载失败`);
          // 给一些额外时间再试
          await sleep(2000);
          const retryFloor = document.querySelector(`div[data-layer-index="${currentIndex - 1}"]`);
          if (!retryFloor) {
            console.error(`❌ 第 ${currentIndex - 1} 层确实无法加载`);
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
      await sleep(1500);
      
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
      console.log("⏸️ 游戏未开始或已结束（没有可点击的门）");
      return false;
    }
  }

  // 主循环
  let roundCount = 0;
  let noGameCount = 0;
  const maxNoGameCount = 5;  // 减少到5次
  
  console.log("🎮 === 浏览器自动爬楼脚本启动 ===");
  console.log("📝 说明：脚本会自动检测并点击可用的门");
  
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
          console.log("💡 提示：如需重新开始，请刷新页面后再次运行脚本");
          break;
        }
      }
      
      // 等待一段时间再进行下一轮
      await sleep(3000 + Math.random() * 2000);
      
    } catch (e) {
      console.error("❌ 发生错误:", e);
      await sleep(5000);
    }
  }
  
  console.log("🛑 脚本已停止");
})();